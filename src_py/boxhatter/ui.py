from pathlib import Path
import datetime

from hat import aio
import aiohttp.web

from boxhatter import common
import boxhatter.server


static_dir: Path = common.package_path / 'ui'


async def create(host: str,
                 port: int,
                 server: boxhatter.server.Server
                 ) -> 'UI':
    ui = UI()
    ui._server = server
    ui._async_group = aio.Group()

    app = aiohttp.web.Application()
    get_routes = (
        aiohttp.web.get(path, handler) for path, handler in (
            ('/', ui._process_get_root),
            ('/repo/{repo}', ui._process_get_repo),
            ('/repo/{repo}/commit/{commit}', ui._process_get_commit)))
    post_routes = (
        aiohttp.web.post(path, handler) for path, handler in (
            ('/repo/{repo}/run', ui._process_post_run),
            ('/repo/{repo}/commit/{commit}/remove', ui._process_post_remove)))
    webhook_route = aiohttp.web.route('*', '/repo/{repo}/webhook',
                                      ui._process_webhook)
    static_route = aiohttp.web.static('/', static_dir)
    app.add_routes([*get_routes, *post_routes, webhook_route, static_route])

    runner = aiohttp.web.AppRunner(app)
    await runner.setup()
    ui.async_group.spawn(aio.call_on_cancel, runner.cleanup)

    try:
        site = aiohttp.web.TCPSite(runner=runner,
                                   host=host,
                                   port=port,
                                   shutdown_timeout=0.1,
                                   reuse_address=True)
        await site.start()

    except BaseException:
        await aio.uncancellable(ui.async_group.async_close())
        raise

    return ui


class UI(aio.Resource):

    @property
    def async_group(self):
        return self._async_group

    async def _process_get_root(self, request):
        commits = await self._server.get_commits(None)

        body = (f'{_generate_repos(self._server.repos)}\n'
                f'{_generate_commits(commits)}')
        return _create_html_response('Box Hatter', body)

    async def _process_get_repo(self, request):
        repo = self._get_repo(request)
        commits = await self._server.get_commits(repo)

        title = f'Box Hatter - {repo}'
        body = (f'{_generate_commits(commits)}\n'
                f'{_generate_run(repo)}')
        return _create_html_response(title, body)

    async def _process_get_commit(self, request):
        commit = await self._get_commit(request)

        title = f'Box Hatter - {commit.repo}/{commit.hash}'
        body = _generate_commit(commit)
        return _create_html_response(title, body)

    async def _process_post_run(self, request):
        repo = self._get_repo(request)

        body = await request.post()
        commit_hash = body['hash']
        if not commit_hash:
            raise aiohttp.web.HTTPBadRequest()

        commit = await self._server.run_commit(repo, commit_hash)

        url = f'/repo/{commit.repo}/commit/{commit.hash}'
        raise aiohttp.web.HTTPFound(url)

    async def _process_post_remove(self, request):
        commit = await self._get_commit(request)

        await self._server.remove_commit(commit)

        raise aiohttp.web.HTTPFound(f'/repo/{commit.repo}')

    async def _process_webhook(self, request):
        repo = self._get_repo(request)

        self._server.sync_repo(repo)
        return aiohttp.web.Response()

    def _get_repo(self, request):
        repo = request.match_info['repo']
        if repo not in self._server.repos:
            raise aiohttp.web.HTTPBadRequest()
        return repo

    async def _get_commit(self, request):
        repo = self._get_repo(request)
        commit_hash = request.match_info['commit']
        commit = await self._server.get_commit(repo, commit_hash)
        if not commit:
            raise aiohttp.web.HTTPBadRequest()
        return commit


def _create_html_response(title, body):
    text = _html_template.format(title=title,
                                 body=body)
    return aiohttp.web.Response(content_type='text/html',
                                text=text)


def _generate_repos(repos):
    items = '\n'.join(f'<li><a href="/repo/{repo}">{repo}</a></li>'
                      for repo in repos)
    return (f'<div class="repos">\n'
            f'<h2>Repositories</h2>\n'
            f'<ul>\n'
            f'{items}\n'
            f'</ul>\n'
            f'</div>')


def _generate_commits(commits):
    thead = ('<tr>\n'
             '<th class="col-change">Change</th>\n'
             '<th class="col-repo">Repo</th>\n'
             '<th class="col-hash">Commit</th>\n'
             '<th class="col-status">Status</th>\n'
             '</tr>')

    tbody = '\n'.join(
        (f'<tr>\n'
         f'<td class="col-change">{_format_time(commit.change)}</td>\n'
         f'<td class="col-repo">{_generate_repo_link(commit.repo)}</td>\n'
         f'<td class="col-hash">{_generate_commit_link(commit)}</td>\n'
         f'<td class="col-status">{commit.status.name}</td>\n'
         f'</tr>')
        for commit in commits)

    return (f'<div class="commits">\n'
            f'<h2>Commits</h2>\n'
            f'<table>\n'
            f'<thead>\n'
            f'{thead}\n'
            f'</thead>\n'
            f'<tbody>\n'
            f'{tbody}\n'
            f'</tbody>\n'
            f'</table>\n'
            f'</div>')


def _generate_commit(commit):
    run_action = f'/repo/{commit.repo}/run'
    run_button = (f'<form method="post" action="{run_action}">\n'
                  f'<input type="hidden" name="hash" value="{commit.hash}">\n'
                  f'<input type="submit" value="Run commit">\n'
                  f'</form>')

    remove_action = f'/repo/{commit.repo}/commit/{commit.hash}/remove'
    remove_button = (f'<form method="post" action="{remove_action}">\n'
                     f'<input type="submit" value="Remove commit">\n'
                     f'</form>')

    repo_link = _generate_repo_link(commit.repo)

    return (f'<div class="commit">\n'
            f'<label>Repo:</label><div>{repo_link}</div>\n'
            f'<label>Commit:</label><div>{commit.hash}</div>\n'
            f'<label>Change:</label><div>{_format_time(commit.change)}</div>\n'
            f'<label>Status:</label><div>{commit.status.name}</div>\n'
            f'<label>Output:</label><pre>{commit.output}</pre>\n'
            f'<label></label><div>{run_button}{remove_button}</div>\n'
            f'</div>')


def _generate_run(repo):
    return (f'<div class="run">\n'
            f'<form method="post" action="/repo/{repo}/run">\n'
            f'<input type="text" name="hash">\n'
            f'<input type="submit" value="Run commit">\n'
            f'</form>\n'
            f'</div>')


def _generate_repo_link(repo):
    return f'<a href="/repo/{repo}">{repo}</a>'


def _generate_commit_link(commit):
    url = f'/repo/{commit.repo}/commit/{commit.hash}'
    return f'<a href="{url}">{commit.hash}</a>'


def _format_time(t):
    return datetime.datetime.fromtimestamp(t).strftime("%Y-%m-%d %H:%M:%S")


_html_template = r"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<link href="/main.css" rel="stylesheet">
</head>
<body>
{body}
</body>
</html>
"""
