import asyncio
import aiohttp.web


async def create_web_server(backend, host, port, webhook_path, web_path):
    srv = WebServer()
    srv._backend = backend
    srv._app = aiohttp.web.Application()
    srv._app.router.add_route(
        'GET', '/', lambda req: aiohttp.web.HTTPFound('/index.html'))
    srv._app.router.add_route('*', '/ws', srv._ws_handler)
    srv._app.router.add_route('POST', webhook_path, srv._webhook_handler)
    srv._app.router.add_static('/', web_path)
    srv._app_handler = srv._app.make_handler()
    srv._srv = await asyncio.get_event_loop().create_server(
        srv._app_handler, host=host, port=port)
    return srv


class WebServer:

    async def async_close(self):
        self._srv.close()
        await self._srv.wait_closed()
        await self._app.shutdown()
        await self._app_handler.finish_connections(0)
        await self._app.cleanup()

    async def _ws_handler(self, request):
        ws = aiohttp.web.WebSocketResponse()
        await ws.prepare(request)
        client = Client(self._backend, ws)
        await client.run()
        return ws

    async def _webhook_handler(self, request):
        pass


class Client:

    def __init__(self, backend, ws):
        pass

    async def run(self):
        pass
