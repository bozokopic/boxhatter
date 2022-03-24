from pathlib import Path

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
    app.add_routes([
        aiohttp.web.get('/', ui._get_root_handler),
        aiohttp.web.get('/repo/{repo}', server._get_repo_handler),
        aiohttp.web.get('/repo/{repo}/commit/{commit}',
                        server._get_commit_handler),
        aiohttp.web.post('/repo/{repo}/webhook',
                         server._post_webhook_handler),
        aiohttp.web.post('/repo/{repo}/commit/{commit}/run',
                         server._post_run_handler),
        aiohttp.web.post('/repo/{repo}/commit/{commit}/remove',
                         server._post_remove_handler),
        aiohttp.web.static('/', static_dir)])

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
        pass

    async def _get_repo_handler(self, request):
        pass

    async def _get_commit_handler(self, request):
        pass

    async def _post_webhook_handler(self, request):
        pass

    async def _post_run_handler(self, request):
        pass

    async def _post_remove_handler(self, request):
        pass
