import asyncio
import json
import aiohttp.web

from hatter import util
import hatter.json_validator


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
        client = _Client(self._backend, ws)
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


_WebhookRequest = util.namedtuple('_WebhookRequest', 'url', 'commits')


def _parse_webhook_request(headers, data):
    if headers.get('X-Gitlab-Event') == 'Push Hook':
        url = data['repository']['git_http_url']
        commits = [commit['id'] for commit in data['commits']]
    elif headers.get('X-GitHub-Event') == 'push':
        url = data['repository']['clone_url']
        commits = [commit['id'] for commit in data['commits']]
    else:
        raise Exception('unsupported webhook event')
    return _WebhookRequest(url, commits)


class _Client:

    def __init__(self, backend, ws):
        self._backend = backend
        self._ws = ws
        self._log_offset = 0
        self._log_limit = 0
        self._log_entries = []
        self._active_job = None
        self._job_queue = []

    async def run(self):
        self._active_job = self._backend.active
        self._job_queue = list(self._backend.queue)
        with self._backend.register_active_change_cb(self._on_active_change):
            with self._backend.register_queue_change_cb(self._on_queue_change):
                with self._backend.register_log_change_cb(self._on_log_change):
                    try:
                        self._send_active_job()
                        self._send_job_queue()
                        self._send_log_entries()
                        while True:
                            msg = await self._ws.receive()
                            if self._ws.closed:
                                break
                            if msg.type != aiohttp.WSMsgType.TEXT:
                                continue
                            json_msg = json.loads(msg.data, encoding='utf-8')
                            hatter.json_validator.validate(json_msg, 'hatter://message.yaml#/definitions/client_message')  # NOQA
                            await self._process_msg(json_msg)
                    except Exception as e:
                        print('>>>', e)

    async def _process_msg(self, msg):
        if msg['type'] == 'set_log':
            self._log_offset = msg['log_offset']
            self._log_limit = msg['log_limit']
            await self._update_log()
        elif msg['type'] == 'add_job':
            await self._backend.add_job(msg['repository'], msg['commit'])

    def _on_active_change(self):
        if self._active_job != self._backend.active:
            self._active_job = self._backend.active
            self._send_active_job()

    def _on_queue_change(self):
        if self._job_queue != self._backend.job_queue:
            self._job_queue = list(self._backend.job_queue)
            self._send_job_queue()

    def _on_log_change(self):
        asyncio.ensure_future(self._update_log())

    async def _update_log(self, offset, limit):
        log_entries = await self._backend.query_log(offset, limit)
        if log_entries != self._log_entries:
            self._log_entries = log_entries
            self._send_log_entries()

    def _send_active_job(self):
        self._ws.send_str(json.dumps({
            'type': 'active_job',
            'job': _job_to_json(self._active_job)}))

    def _send_job_queue(self):
        self._ws.send_str(json.dumps({
            'type': 'job_queue',
            'jobs': [_job_to_json(i) for i in self._job_queue]}))

    def _send_log_entries(self):
        self._ws.send_str(json.dumps({
            'type': 'log_entries',
            'entries': [_log_entry_to_json(i) for i in self._log_entries]}))


def _job_to_json(job):
    return {'id': job.id,
            'timestamp': job.timestamp.timestamp(),
            'repository': job.repository,
            'commit': job.commit}


def _log_entry_to_json(entry):
    return {'timestamp': entry.timestamp.timestamp(),
            'repository': entry.repository,
            'commit': entry.commit,
            'message': entry.msg}
