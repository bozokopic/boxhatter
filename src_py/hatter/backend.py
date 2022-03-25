from pathlib import Path
import typing

from hat import aio

from hatter import common


async def create(db_path: Path
                 ) -> 'Backend':
    backend = Backend()
    backend._async_group = aio.Group()
    backend._executor = aio.create_executor(1)

    backend._db = await backend._executor(_ext_create, db_path)
    backend.async_group.spawn(aio.call_on_cancel, backend._executor,
                              _ext_close, backend._db)

    return backend


class Backend(aio.Resource):

    @property
    def async_group(self):
        return self._async_group

    async def get_commits(self,
                          repo: typing.Optional[str],
                          statuses: typing.Optional[typing.Set[common.Status]],
                          order: common.Order
                          ) -> typing.List[common.Commit]:
        return await self.async_group.spawn(
            self._executor, _ext_get_commits, self._db, repo, statuses, order)

    async def get_commit(self,
                         repo: str,
                         commit_hash: str
                         ) -> typing.Optional[common.Commit]:
        return await self.async_group.spawn(
            self._executor, _ext_get_commit, self._db, repo, commit_hash)

    async def update_commit(self, commit: common.Commit):
        return await self._async_group.spawn(
            self._executor, _ext_update_commit, self._db, commit)

    async def remove_commit(self, commit: common.Commit):
        return await self.async_group.spawn(
            self._executor, _ext_remove_commit, self._db, commit)


def _ext_create(db_path):
    pass


def _ext_close(db):
    pass


def _ext_get_commits(db, repo, statuses, order):
    return []


def _ext_get_commit(db, repo, commit_hash):
    pass


def _ext_update_commit(db, commit):
    pass


def _ext_remove_commit(db, commit):
    pass
