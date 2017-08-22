import collections
import sys
import contextlib
import asyncio
import datetime
import sqlite3


def namedtuple(name, *props):
    """Create documented namedtuple

    Args:
        name (Union[str,Tuple[str,str]]):
            named tuple's name or named tuple's name with documentation
        props (Sequence[Union[str,Tuple[str,str]]]):
            named tuple' properties with optional documentation

    Returns:
        class implementing collections.namedtuple

    """
    props = [(i, None) if isinstance(i, str) else i for i in props]
    cls = collections.namedtuple(name if isinstance(name, str) else name[0],
                                 [i[0] for i in props])
    if not isinstance(name, str) and name[1]:
        cls.__doc__ = name[1]
    for k, v in props:
        if v:
            getattr(cls, k).__doc__ = v
    try:
        cls.__module__ = sys._getframe(1).f_globals.get('__name__', '__main__')
    except (AttributeError, ValueError):
        pass
    return cls


def run_until_complete_without_interrupt(future):
    """Run event loop until future or coroutine is done

    Args:
        future (Awaitable): future or coroutine

    Returns:
        Any: provided future's result

    KeyboardInterrupt is suppressed (while event loop is running) and is mapped
    to single cancelation of running task. If multipple KeyboardInterrupts
    occur, task is cancelled only once.

    """
    async def ping_loop():
        with contextlib.suppress(asyncio.CancelledError):
            while True:
                await asyncio.sleep(1)

    task = asyncio.ensure_future(future)
    if sys.platform == 'win32':
        ping_loop_task = asyncio.ensure_future(ping_loop())
    with contextlib.suppress(KeyboardInterrupt):
        asyncio.get_event_loop().run_until_complete(task)
    asyncio.get_event_loop().call_soon(task.cancel)
    if sys.platform == 'win32':
        asyncio.get_event_loop().call_soon(ping_loop_task.cancel)
    while not task.done():
        with contextlib.suppress(KeyboardInterrupt):
            asyncio.get_event_loop().run_until_complete(task)
    if sys.platform == 'win32':
        while not ping_loop_task.done():
            with contextlib.suppress(KeyboardInterrupt):
                asyncio.get_event_loop().run_until_complete(ping_loop_task)
    return task.result()


def monkeypatch_sqlite3():
    """Monkeypatch sqlite timestamp converter"""

    def _sqlite_convert_timestamp(val):
        datepart, timetzpart = val.split(b" ")
        if b"+" in timetzpart:
            tzsign = 1
            timepart, tzpart = timetzpart.split(b"+")
        elif b"-" in timetzpart:
            tzsign = -1
            timepart, tzpart = timetzpart.split(b"-")
        else:
            timepart, tzpart = timetzpart, None
        year, month, day = map(int, datepart.split(b"-"))
        timepart_full = timepart.split(b".")
        hours, minutes, seconds = map(int, timepart_full[0].split(b":"))
        if len(timepart_full) == 2:
            microseconds = int('{:0<6.6}'.format(timepart_full[1].decode()))
        else:
            microseconds = 0
        if tzpart:
            tzhours, tzminutes = map(int, tzpart.split(b":"))
            tz = datetime.timezone(
                tzsign * datetime.timedelta(hours=tzhours, minutes=tzminutes))
        else:
            tz = None

        val = datetime.datetime(year, month, day, hours, minutes, seconds,
                                microseconds, tz)
        return val

    sqlite3.register_converter("timestamp", _sqlite_convert_timestamp)


class RegisterCallbackHandle(collections.namedtuple(
        'RegisterCallbackHandle', ['cancel'])):
    """Handle used for canceling callback registration

    Attributes:
        cancel (Callable[[],None]): cancel registered callback

    """

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.cancel()


class CallbackRegistry:
    """Callback registry"""

    def __init__(self):
        self._cbs = []

    def register(self, cb):
        """Register callback

        Args:
            cb (Callable): callback

        Returns:
            RegisterCallbackHandle

        """
        self.cbs.append(cb)
        return RegisterCallbackHandle(lambda: self.cbs.remove(cb))

    def notify(self, *args, **kwargs):
        """Notify all registered callbacks"""

        for cb in self._cbs:
            cb(*args, **kwargs)
