import asyncio
import collections
import contextlib
import itertools
import multiprocessing
import os
import subprocess
import sys
import time
import typing

from hat import aio
from hat import json

from boxhatter import common
import boxhatter.backend


async def create(conf: json.Data,
                 backend: boxhatter.backend.Backend
                 ) -> 'Server':
    server = Server()
    server._conf = conf
    server._backend = backend
    server._async_group = aio.Group()
    server._repos = set(conf['repos'].keys())
    server._run_queue = aio.Queue()
    server._sync_events = {}

    for repo, repo_conf in conf['repos'].items():
        sync_event = asyncio.Event()
        server._sync_events[repo] = sync_event
        server.async_group.spawn(server._sync_loop, repo, repo_conf,
                                 sync_event)

    for _ in range(multiprocessing.cpu_count()):
        server.async_group.spawn(server._run_loop)

    try:
        commits = await backend.get_commits(repo=None,
                                            statuses={common.Status.PENDING,
                                                      common.Status.RUNNING},
                                            order=common.Order.ASC)

        for commit in commits:
            commit = commit._replace(change=int(time.time()),
                                     status=common.Status.PENDING,
                                     output='')
            await backend.update_commit(commit)
            server._run_queue.put_nowait(commit)

    except BaseException:
        await aio.uncancellable(server.async_close())
        raise

    return server


class Server(aio.Resource):

    @property
    def async_group(self):
        return self._async_group

    @property
    def repos(self) -> typing.Set[str]:
        return self._repos

    async def get_commits(self,
                          repo: typing.Optional[str],
                          ) -> typing.List[common.Commit]:
        return await self._backend.get_commits(repo=repo,
                                               statuses=None,
                                               order=common.Order.DESC)

    async def get_commit(self,
                         repo: str,
                         commit_hash: str
                         ) -> typing.Optional[common.Commit]:
        return await self._backend.get_commit(repo, commit_hash)

    async def run_commit(self,
                         repo: str,
                         commit_hash: str
                         ) -> common.Commit:
        commit = common.Commit(repo=repo,
                               hash=commit_hash,
                               change=int(time.time()),
                               status=common.Status.PENDING,
                               output='')
        await self._backend.update_commit(commit)
        self._run_queue.put_nowait(commit)
        return commit

    def sync_repo(self, repo: str):
        self._sync_events[repo].set()

    async def remove_commit(self, commit: common.Commit):
        await self._backend.remove_commit(commit)

    async def _sync_loop(self, repo, repo_conf, sync_event):
        try:
            url = repo_conf['url']
            refs = repo_conf.get('refs', ['refs/heads/*'])
            min_sync_delay = repo_conf.get('min_sync_delay', 60) or 0
            max_sync_delay = repo_conf.get('max_sync_delay')
            last_sync = time.monotonic() - min_sync_delay

            while True:
                dt = time.monotonic() - last_sync
                if dt < min_sync_delay:
                    await asyncio.sleep(min_sync_delay - dt)

                sync_event.clear()
                commit_hashes = await _git_ls_remote(url, refs)
                last_sync = time.monotonic()

                for commit_hash in commit_hashes:
                    commit = await self._backend.get_commit(repo, commit_hash)
                    if commit:
                        continue
                    await self.run_commit(repo, commit_hash)

                if max_sync_delay is None:
                    await sync_event.wait()

                else:
                    with contextlib.suppress(asyncio.TimeoutError):
                        await asyncio.wait_for(sync_event.wait(),
                                               max_sync_delay)

        finally:
            self.close()

    async def _run_loop(self):
        try:
            while True:
                commit = await self._run_queue.get()
                repo_conf = self._conf['repos'][commit.repo]
                action = repo_conf.get('action', '.boxhatter.yaml')
                env = {**self._conf.get('env', {}),
                       **repo_conf.get('env', {})}
                url = repo_conf['url']
                ref = commit.hash

                commit = commit._replace(change=int(time.time()),
                                         status=common.Status.RUNNING,
                                         output='')
                await self._backend.update_commit(commit)

                try:
                    output = await _execute(action=action,
                                            env=env,
                                            url=url,
                                            ref=ref)
                    status = common.Status.SUCCESS

                except Exception as e:
                    output = str(e)
                    status = common.Status.FAILURE

                commit = commit._replace(change=int(time.time()),
                                         status=status,
                                         output=output)
                await self._backend.update_commit(commit)

        finally:
            self.close()


async def _execute(action, env, url, ref):
    cmd = [sys.executable, '-m', 'boxhatter',
           '--log-level', common.settings.log_level,
           *(['--ssh-key', common.settings.ssh_key]
             if common.settings.ssh_key else []),
           '--engine', common.settings.engine,
           'execute',
           '--action', action,
           *itertools.chain.from_iterable(('--env', i) for i in env),
           url, ref]

    p = await asyncio.create_subprocess_exec(*cmd,
                                             stdin=subprocess.DEVNULL,
                                             stdout=subprocess.PIPE,
                                             stderr=subprocess.STDOUT,
                                             env={**os.environ, **env})

    try:
        output, _ = await p.communicate()
        output = str(output, encoding='utf-8', errors='ignore')

        if p.returncode:
            raise Exception(output)

        return output

    finally:
        if p.returncode is None:
            p.terminate()


async def _git_ls_remote(url, refs):
    cmd = ['git', 'ls-remote', url, *refs]

    p = await asyncio.create_subprocess_exec(*cmd,
                                             stdin=subprocess.DEVNULL,
                                             stdout=subprocess.PIPE,
                                             stderr=subprocess.PIPE)

    try:
        stdout, stderr = await p.communicate()
        if p.returncode:
            stderr = str(stderr, encoding='utf-8', errors='ignore')
            raise Exception(stderr)

        result = collections.deque()
        stdout = str(stdout, encoding='utf-8', errors='ignore')

        for line in stdout.split('\n'):
            segments = line.split(maxsplit=1)
            if not segments:
                continue
            result.append(segments[0])

        return result

    except Exception:
        return []

    finally:
        if p.returncode is None:
            p.terminate()
