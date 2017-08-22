import sqlite3
import datetime
import threading
import logging
import concurrent.futures
import asyncio

from hatter import util
from hatter import executor


util.monkeypatch_sqlite3()


LogEntry = util.namedtuple('LogEntry',
                           ['timestamp', 'datetime.datetime: timestamp'],
                           ['repository', 'str: repository'],
                           ['commit', 'str: commit'],
                           ['msg', 'str: message'])

Job = util.namedtuple('Job',
                      ['id', 'int: id'],
                      ['timestamp', 'datetime.datetime: timestamp'],
                      ['repository', 'str: repository'],
                      ['commit', 'str: commit'])


class Backend:

    def __init__(self, db_path):
        self._next_job_id = 0
        self._active = None
        self._queue = []
        self._active_change_cbs = util.CallbackRegistry()
        self._queue_change_cbs = util.CallbackRegistry()
        self._log_change_cbs = util.CallbackRegistry()
        self._cv = asyncio.Condition()
        self._db = _DB(db_path)
        self._executor = concurrent.futures.ThreadPoolExecutor()
        self._run_loop_future = asyncio.ensure_future(self._run_loop())

    @property
    def active(self):
        self._active

    @property
    def queue(self):
        return self._queue

    def register_active_change_cb(self, cb):
        return self._active_change_cbs.register(cb)

    def register_queue_change_cb(self, cb):
        return self._queue_change_cbs.register(cb)

    def register_log_change_cb(self, cb):
        return self._log_change_cbs.register(cb)

    async def async_close(self):
        self._run_loop_future.cancel()
        await self._run_loop_future

    async def query_log(self, offset, limit):
        return await asyncio.get_event_loop().run_in_executor(
            self._executor, self._db.query, offset, limit)

    async def add_job(self, repository, commit):
        job = Job(id=self._next_job_id,
                  timestamp=datetime.datetime.now(datetime.timezone.utc),
                  repository=repository,
                  commit=commit)
        self._next_job_id += 1
        with await self._cv:
            self._queue.append(job)
            self._cv.notify_all()
        self._queue_change_cbs.notify()

    async def _run_loop(self):
        log = logging.getLogger('hatter.project')
        while True:
            with await self._cv:
                while not self._queue:
                    await self._cv.wait()
                self._active = self._queue_change_cbs.pop(0)
            self._queue_change_cbs.notify()
            self._active_change_cbs.notify()

            handler = _LogHandler(
                self._db, self._active.repository, self._active.commit)
            log.addHandler(handler)
            try:
                await asyncio.get_event_loop().run_in_executor(
                    self._executor, executor.run,
                    log, self._active.repository, self._active.commit)
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error("%s", e, exc_info=True)
            finally:
                log.removeHandler(handler)
                self._active = None
                self._active_change_cbs.notify()


class _LogHandler(logging.Handler):

    def __init__(self, db, repository, commit):
        super().__init__()
        self._db = db
        self._repository
        self._commit = commit

    def emit(self, record):
        self._db.add(
            timestamp=datetime.datetime.fromtimestamp(
                record.created, datetime.timezone.utc),
            repository=self._repository,
            commit=self._commit,
            msg=record.getMessage())


class _DB:

    def __init__(self, db_path):
        db_path.parent.mkdir(exist_ok=True)
        self._db = sqlite3.connect('file:{}?nolock=1'.format(db_path),
                                   uri=True,
                                   isolation_level=None,
                                   detect_types=sqlite3.PARSE_DECLTYPES)
        self._db.executescript("CREATE TABLE IF NOT EXISTS log ("
                               "timestamp TIMESTAMP, "
                               "repository TEXT, "
                               "commit TEXT, "
                               "msg TEXT)")
        self._db.commit()
        self._lock = threading.Lock()

    def close(self):
        with self._lock:
            self._db.close()

    def add(self, timestamp, repository, commit, msg):
        with self._lock:
            self._db.execute(
                "INSERT INTO log VALUES "
                "(:timestamp, :repository, :commit, :msg)",
                {'timestamp': timestamp,
                 'repository': repository,
                 'commit': commit,
                 'msg': msg})

    def query(self, offset, limit):
        with self._lock:
            c = self._db.execute(
                "SELECT rowid, * FROM log ORDER BY rowid DESC "
                "LIMIT :limit OFFSET :offset",
                {'limit': limit, 'offset': offset})
            try:
                result = c.fetchall()
            except Exception as e:
                result = []
            return [LogEntry(timestamp=i[1],
                             repository=i[2],
                             commit=i[3],
                             msg=i[4])
                    for i in result]
