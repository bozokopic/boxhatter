from pathlib import Path
import sqlite3
import typing

from hat import aio

from boxhatter import common


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
        await self._async_group.spawn(
            self._executor, _ext_update_commit, self._db, commit)

    async def remove_commit(self, commit: common.Commit):
        await self.async_group.spawn(
            self._executor, _ext_remove_commit, self._db, commit)


def _ext_create(db_path):
    db_path.parent.mkdir(exist_ok=True)
    db = sqlite3.connect(f'file:{db_path}?nolock=1',
                         uri=True,
                         isolation_level=None,
                         detect_types=sqlite3.PARSE_DECLTYPES)

    try:
        db.executescript(r"""
            PRAGMA journal_mode = OFF;
            CREATE TABLE IF NOT EXISTS commits (
                repo TEXT,
                hash TEXT,
                change INTEGER,
                status INTEGER,
                output TEXT,
                PRIMARY KEY (repo, hash) ON CONFLICT REPLACE
            );
            CREATE INDEX IF NOT EXISTS commits_change_index ON commits (
                change
            )""")

    except Exception:
        db.close()
        raise

    return db


def _ext_close(db):
    db.close()


def _ext_get_commits(db, repo, statuses, order):
    cmd = "SELECT * FROM commits"
    where = []
    if repo:
        where.append("repo = :repo")
    if statuses:
        status_values = (str(status.value) for status in statuses)
        where.append(f"status IN ({', '.join(status_values)})")
    if where:
        cmd += f" WHERE {' AND '.join(where)}"
    cmd += f" ORDER BY change {order.value}"
    args = {'repo': repo}
    cur = db.execute(cmd, args)
    return [_commit_from_row(row) for row in cur]


def _ext_get_commit(db, repo, commit_hash):
    cmd = "SELECT * FROM commits WHERE repo = :repo AND hash = :hash"
    args = {'repo': repo,
            'hash': commit_hash}
    cur = db.execute(cmd, args)
    row = cur.fetchone()
    return _commit_from_row(row) if row else None


def _ext_update_commit(db, commit):
    cmd = ("INSERT OR REPLACE INTO commits VALUES "
           "(:repo, :hash, :change, :status, :output)")
    args = {'repo': commit.repo,
            'hash': commit.hash,
            'change': commit.change,
            'status': commit.status.value,
            'output': commit.output}
    db.execute(cmd, args)


def _ext_remove_commit(db, commit):
    cmd = "DELETE FROM commits WHERE repo = :repo AND hash = :hash"
    args = {'repo': commit.repo,
            'hash': commit.hash}
    db.execute(cmd, args)


def _commit_from_row(row):
    return common.Commit(repo=row[0],
                         hash=row[1],
                         change=row[2],
                         status=common.Status(row[3]),
                         output=row[4])
