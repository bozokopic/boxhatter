from pathlib import Path
import contextlib
import datetime
import time
import uuid

from hat import aio
import aiohttp.web

from boxhatter import common
import boxhatter.server


static_dir: Path = common.package_path / 'ui'

pagination_limit: int = 20


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
            ('/feed', ui._process_get_feed),
            ('/repo/{repo}', ui._process_get_repo),
            ('/repo/{repo}/commit/{commit}', ui._process_get_commit),
            ('/repo/{repo}/feed', ui._process_get_feed)))
    post_routes = (
        aiohttp.web.post(path, handler) for path, handler in (
            ('/repo/{repo}/run', ui._process_post_run),
            ('/repo/{repo}/clear', ui._process_post_clear),
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
    def async_group(self) -> aio.Group:
        return self._async_group

    async def _process_get_root(self, request):
        page = self._get_page(request)
        offset = page * pagination_limit
        commits = await self._server.get_commits(repo=None,
                                                 limit=pagination_limit + 1,
                                                 offset=offset)
        commits, more_follows = (commits[:pagination_limit],
                                 len(commits) > pagination_limit)

        body = (f'{_generate_repos(self._server.repos)}\n'
                f'{_generate_commits(commits)}\n'
                f'{_generate_pagination(page, more_follows)}')
        return _create_html_response('Box Hatter', body, '/feed')

    async def _process_get_repo(self, request):
        repo = self._get_repo(request)
        page = self._get_page(request)
        offset = page * pagination_limit
        commits = await self._server.get_commits(repo=repo,
                                                 limit=pagination_limit + 1,
                                                 offset=offset)
        commits, more_follows = (commits[:pagination_limit],
                                 len(commits) > pagination_limit)

        title = f'Box Hatter - {repo}'
        body = (f'{_generate_commits(commits)}\n'
                f'{_generate_pagination(page, more_follows)}\n'
                f'{_generate_run(repo)}\n'
                f'{_generate_clear(repo)}')
        feed_url = f'/repo/{repo}/feed'
        return _create_html_response(title, body, feed_url)

    async def _process_get_commit(self, request):
        commit = await self._get_commit(request)

        title = f'Box Hatter - {commit.repo}/{commit.hash}'
        body = _generate_commit(commit)
        feed_url = f'/repo/{commit.repo}/feed'
        return _create_html_response(title, body, feed_url)

    async def _process_get_feed(self, request):
        repo = (self._get_repo(request) if 'repo' in request.match_info
                else None)
        commits = await self._server.get_commits(repo)

        title = 'All repositories' if repo is None else f'Repository {repo}'
        text = _generate_feed(self._server.server_uuid, title, commits)
        return aiohttp.web.Response(content_type='application/atom+xml',
                                    text=text)

    async def _process_post_run(self, request):
        repo = self._get_repo(request)

        body = await request.post()
        commit_hash = body['hash']
        if not commit_hash:
            raise aiohttp.web.HTTPBadRequest()

        commit = await self._server.run_commit(repo, commit_hash)

        url = f'/repo/{commit.repo}/commit/{commit.hash}'
        raise aiohttp.web.HTTPFound(url)

    async def _process_post_clear(self, request):
        repo = self._get_repo(request)

        await self._server.clear_cache(repo)

        raise aiohttp.web.HTTPFound(f'/repo/{repo}')

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

    def _get_page(self, request):
        page_str = request.query.get('page', '0')
        with contextlib.suppress(ValueError):
            page = int(page_str)
            if page >= 0:
                return page
        raise aiohttp.web.HTTPBadRequest()

    async def _get_commit(self, request):
        repo = self._get_repo(request)
        commit_hash = request.match_info['commit']
        commit = await self._server.get_commit(repo, commit_hash)
        if not commit:
            raise aiohttp.web.HTTPBadRequest()
        return commit


def _create_html_response(title, body, feed_url):
    text = (f'<!DOCTYPE html>\n'
            f'<html>\n'
            f'<head>\n'
            f'<meta charset="UTF-8">\n'
            f'<meta name="viewport" content="width=device-width, initial-scale=1">\n'  # NOQA
            f'<title>{title}</title>\n'
            f'<link href="{feed_url}" type="application/atom+xml" rel="alternate" title="{title} feed">\n'  # NOQA
            f'<link href="/main.css" rel="stylesheet">\n'
            f'</head>\n'
            f'<body>\n'
            f'{body}\n'
            f'</body>\n'
            f'</html>\n')
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


def _generate_pagination(page, more_follows):
    content = ''

    if page > 0:
        content += (f'<a class="previous" href="?page={page - 1}">'
                    f'&lt; Previous'
                    f'</a>')

    if more_follows:
        content += (f'<a class="next" href="?page={page + 1}">'
                    f'Next &gt;'
                    f'</a>')

    return f'<div class="pagination">{content}</div>'


def _generate_run(repo):
    return (f'<div class="run">\n'
            f'<form method="post" action="/repo/{repo}/run">\n'
            f'<input type="text" name="hash">\n'
            f'<input type="submit" value="Run commit">\n'
            f'</form>\n'
            f'</div>')


def _generate_clear(repo):
    return (f'<div class="clear">\n'
            f'<form method="post" action="/repo/{repo}/clear">\n'
            f'<input type="submit" value="Clear cache">\n'
            f'</form>\n'
            f'</div>')


def _generate_repo_link(repo):
    return f'<a href="/repo/{repo}">{repo}</a>'


def _generate_commit_link(commit):
    url = f'/repo/{commit.repo}/commit/{commit.hash}'
    return f'<a href="{url}">{commit.hash}</a>'


def _format_time(t):
    return datetime.datetime.fromtimestamp(t).strftime("%Y-%m-%d %H:%M:%S")


def format_feed_time(t):
    dt = datetime.datetime.utcfromtimestamp(t)
    return dt.isoformat(timespec='seconds') + 'Z'


def _generate_feed(server_uuid, title, commits):

    def get_entry_uuid(commit):
        return uuid.uuid5(server_uuid, f'{commit.repo}/{commit.hash}')

    def get_entry_title(commit):
        return f'{commit.repo} - {commit.hash}'

    def get_entry_link(commit):
        return f'/repo/{commit.repo}/commit/{commit.hash}'

    def get_entry_content(commit):
        return (f'Status: {commit.status.name}\n'
                f'Output:\n{commit.output}')

    feed_updated = max((commit.change for commit in commits),
                       default=int(time.time()))

    entries = '\n'.join(
        f'<entry>\n'
        f'<id>urn:uuid:{get_entry_uuid(commit)}</id>\n'
        f'<title>{get_entry_title(commit)}</title>\n'
        f'<link href="{get_entry_link(commit)}" />\n'
        f'<updated>{format_feed_time(commit.change)}</updated>\n'
        f'<content type="text">{get_entry_content(commit)}</content>\n'
        f'</entry>'
        for commit in commits)

    return (f'<?xml version="1.0" encoding="utf-8"?>\n'
            f'<feed xmlns="http://www.w3.org/2005/Atom">\n'
            f'<title>{title}</title>\n'
            f'<id>urn:uuid:{server_uuid}</id>\n'
            f'<author>\n'
            f'<name>boxhatter</name>\n'
            f'</author>\n'
            f'<updated>{format_feed_time(feed_updated)}</updated>\n'
            f'{entries}\n'
            f'</feed>\n')
