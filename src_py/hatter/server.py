import asyncio
import json
import aiohttp.web

from hatter import util


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
        try:
            if not ({'X-Gitlab-Event', 'X-GitHub-Event'} &
                    set(request.headers.keys())):
                raise Exception('unsupported webhook request')
            body = await request.read()
            data = json.loads(body)
            req = _parse_webhook_request(request.headers, data)
            for commit in req.commits:
                self._backend.add_job(req.url, commit)
        except Exception:
            pass
        return aiohttp.web.Response()


class Client:

    def __init__(self, backend, ws):
        pass

    async def run(self):
        pass


WebhookRequest = util.namedtuple('WebhookRequest', 'url', 'commits')


def _parse_webhook_request(headers, data):
    if headers.get('X-Gitlab-Event') == 'Push Hook':
        url = data['repository']['git_http_url']
        commits = [commit['id'] for commit in data['commits']]
    elif headers.get('X-GitHub-Event') == 'push':
        url = data['repository']['clone_url']
        commits = [commit['id'] for commit in data['commits']]
    else:
        raise Exception('unsupported webhook event')
    return WebhookRequest(url, commits)
