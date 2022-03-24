from hat import aio
from hat import json

import hatter.backend


async def create(conf: json.Data,
                 backend: hatter.backend.Backend
                 ) -> 'Server':
    server = Server()
    server._backend = backend
    server._async_group = aio.Group()

    return server


class Server(aio.Resource):

    @property
    def async_group(self):
        return self._async_group
