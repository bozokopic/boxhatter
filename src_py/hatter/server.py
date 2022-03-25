import asyncio
import multiprocessing
import time
import typing

from hat import aio
from hat import json

from hatter import common
import hatter.backend


async def create(conf: json.Data,
                 backend: hatter.backend.Backend
                 ) -> 'Server':
    server = Server()
    server._conf = conf
    server._backend = backend
    server._async_group = aio.Group()
    server._lock = asyncio.Lock()
    server._run_queue = aio.Queue()
    server._sync_events = {}

    for repo, repo_conf in conf['repos'].items():
        sync_event = asyncio.Event()
        server._sync_events[repo] = sync_event
        server.async_group.spawn(server._sync_loop, repo_conf, sync_event)

    for _ in range(multiprocessing.cpu_count()):
        server.async_group.spawn(server._run_loop)

    try:
        commits = await backend.get_commits(repo=None,
                                            statuses={common.Status.PENDING,
                                                      common.Status.RUNNING},
                                            order=common.Order.ASC)

        for commit in commits:
            commit = commit._replace(change=time.time(),
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

    def get_repos(self) -> typing.Iterable[str]:
        return self._conf['repos'].keys()

    async def get_commits(self,
                          repo: typing.Optional[str],
                          ) -> typing.Iterable[common.Commit]:
        if repo and repo not in self._conf['repos']:
            raise ValueError(f'invalid repo {repo}')

        commits = await self._backend.get_commits(repo=repo,
                                                  statuses=None,
                                                  order=common.Order.DESC)

        return commits

    async def get_commit(self,
                         repo: str,
                         commit_hash: str
                         ) -> common.Commit:
        if repo not in self._conf['repos']:
            raise ValueError(f'invalid repo {repo}')

        async with self._lock:
            commit = await self._backend.get_commit(repo, commit_hash)

            if not commit:
                commit = common.Commit(repo=repo,
                                       hash=commit_hash,
                                       change=time.time(),
                                       status=common.Status.PENDING,
                                       output='')
                await self._backend.update_commit(commit)
                self._run_queue.put_nowait(commit)

        return commit

    def sync_repo(self, repo: str):
        self._sync_events[repo].set()

    async def rerun_commit(self,
                           repo: str,
                           commit_hash: str):
        if repo not in self._conf['repos']:
            raise ValueError(f'invalid repo {repo}')

        async with self._lock:
            commit = await self._backend.get_commit(repo, commit_hash)
            if not commit:
                raise ValueError(f'invalid commit {commit_hash}')

            commit = commit._replace(change=time.time(),
                                     status=common.Status.PENDING,
                                     output='')
            await self._backend.update_commit(commit)
            self._run_queue.put_nowait(commit)

    async def remove_commit(self,
                            repo: str,
                            commit_hash: str):
        if repo not in self._conf['repos']:
            raise ValueError(f'invalid repo {repo}')

        async with self._lock:
            commit = await self._backend.get_commit(repo, commit_hash)
            if not commit:
                raise ValueError(f'invalid commit {commit_hash}')

            await self._backend.remove_commit(commit)

    async def _sync_loop(self, repo_conf, sync_event):
        pass

    async def _run_loop(self):
        pass
