from pathlib import Path

from hat import aio


async def create(db_path: Path
                 ) -> 'Backend':
    backend = Backend()
    backend._async_group = aio.Group()

    return backend


class Backend(aio.Resource):

    @property
    def async_group(self):
        return self._async_group
