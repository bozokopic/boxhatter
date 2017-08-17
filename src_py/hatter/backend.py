import sqlite3
import datetime
import threading
import logging

from hatter import util


util.monkeypatch_sqlite3()


LogEntry = util.namedtuple(
    'LogEntry',
    ['timestamp', 'datetime.datetime: timestamp'],
    ['repository', 'str: repository'],
    ['commit', 'str: commit'],
    ['msg', 'str: message'])


class Backend:

    def __init__(self, db_path):
        pass

    async def async_close(self):
        pass

    def add_job(self, url, commit):
        pass


class LogHandler(logging.Handler):

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


class DB:

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
