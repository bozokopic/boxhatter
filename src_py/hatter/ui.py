from pathlib import Path
import datetime

from hat import aio
import aiohttp.web

from hatter import common
import hatter.server


static_dir: Path = common.package_path / 'ui'


async def create(host: str,
                 port: int,
                 server: hatter.server.Server
                 ) -> 'UI':
    ui = UI()
    ui._server = server
    ui._async_group = aio.Group()

    app = aiohttp.web.Application()
    get_routes = (
        aiohttp.web.get(path, handler) for path, handler in (
            ('/', ui._get_root_handler),
            ('/main.css', ui._get_style_handler),
            ('/repo/{repo}', ui._get_repo_handler),
            ('/repo/{repo}/commit/{commit}', ui._get_commit_handler)))
    post_routes = (
        aiohttp.web.post(path, handler) for path, handler in (
            ('/repo/{repo}/webhook', ui._post_webhook_handler),
            ('/repo/{repo}/commit/{commit}/rerun', ui._post_rerun_handler),
            ('/repo/{repo}/commit/{commit}/remove', ui._post_remove_handler)))
    app.add_routes([*get_routes, *post_routes])

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

    async def _get_root_handler(self, request):
        repos = self._server.get_repos()
        commits = await self._server.get_commits(None)
        body = (f'{_generate_repos(repos)}\n'
                f'{_generate_commits(commits)}')
        return _create_html_response('hatter', body)

    async def _get_style_handler(self, request):
        return aiohttp.web.Response(content_type='text/css',
                                    text=_main_css)

    async def _get_repo_handler(self, request):
        repo = request.match_info['repo']
        commits = await self._server.get_commits(repo)
        body = _generate_commits(commits)
        return _create_html_response(f'hatter - {repo}', body)

    async def _get_commit_handler(self, request):
        repo = request.match_info['repo']
        commit_hash = request.match_info['commit']
        commit = await self._server.get_commit(repo, commit_hash)
        body = _generate_commit(commit)
        return _create_html_response(f'hatter - {repo}/{commit_hash}', body)

    async def _post_webhook_handler(self, request):
        repo = request.match_info['repo']
        self._server.sync_repo(repo)
        return aiohttp.web.Response()

    async def _post_rerun_handler(self, request):
        repo = request.match_info['repo']
        commit_hash = request.match_info['commit']
        await self._server.rerun_commit(repo, commit_hash)
        raise aiohttp.web.HTTPFound(f'/repo/{repo}/commit/{commit_hash}')

    async def _post_remove_handler(self, request):
        repo = request.match_info['repo']
        commit_hash = request.match_info['commit']
        await self._server.remove_commit(repo, commit_hash)
        raise aiohttp.web.HTTPFound(f'/repo/{repo}')


def _create_html_response(title, body):
    text = _html_template.format(title=title,
                                 body=body)
    return aiohttp.web.Response(content_type='text/html',
                                text=text)


def _generate_repos(repos):
    items = '\n'.join(f'<li><a href="/repo/{repo}">{repo}</a></li>'
                      for repo in repos)
    return (f'<div class="repos">\n'
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
         f'<td class="col-repo"><a href="/repo/{commit.repo}">{commit.repo}</a></td>\n'  # NOQA
         f'<td class="col-hash"><a href="/repo/{commit.repo}/commit/{commit.hash}">{commit.hash}</a></td>\n'  # NOQA
         f'<td class="col-status">{commit.status.name}</td>\n'
         f'</tr>')
        for commit in commits)

    return (f'<div class="commits">\n'
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
    buttons = '\n'.join(
        (f'<form method="post" action="{action}">\n'
         f'<input type="submit" value="{value}">\n'
         f'</form>')
        for value, action in (
            ('Rerun', f'/repo/{commit.repo}/commit/{commit.hash}/rerun'),
            ('Remove', f'/repo/{commit.repo}/commit/{commit.hash}/remove')))

    return (f'<div class="commit">\n'
            f'<label>Repo:</label><div><a href="/repo/{commit.repo}">{commit.repo}</a></div>\n'  # NOQA
            f'<label>Commit:</label><div>{commit.hash}</div>\n'
            f'<label>Change:</label><div>{_format_time(commit.change)}</div>\n'
            f'<label>Status:</label><div>{commit.status.name}</div>\n'
            f'<label>Output:</label><pre>{commit.output}</pre>\n'
            f'<label></label><div>{buttons}</div>\n'
            f'</div>')


def _format_time(t):
    return datetime.datetime.fromtimestamp(t).strftime("%Y-%m-%d %H:%M:%S")


_html_template = r"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>{title}</title>
<link href="/main.css" rel="stylesheet">
</head>
<body>
{body}
</body>
</html>
"""

_main_css = r"""
.repos {

}

.commits {

}

.commit {

}
"""
