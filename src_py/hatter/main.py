import sys
import asyncio
import argparse
import pdb
import contextlib
import yaml
import logging.config
import atexit
import pkg_resources

import hatter.json_validator
from hatter.backend import Backend
from hatter.server import create_web_server


def main():
    args = _create_parser().parse_args()

    with open(args.conf, encoding='utf-8') as conf_file:
        conf = yaml.safe_load(conf_file)
    hatter.json_validator.validate(conf, 'hatter://server.yaml#')

    if conf['log']:
        logging.config.dictConfig(conf['log'])

    if args.web_path:
        web_path = args.web_path
    else:
        atexit.register(pkg_resources.cleanup_resources)
        web_path = pkg_resources.resource_filename('hatter', 'web')

    _run_until_complete_without_interrupt(async_main(conf, web_path))


async def async_main(conf, web_path):
    backend = None
    web_server = None
    try:
        backend = Backend(conf.get('db_path', 'hatter.db'))
        web_server = await create_web_server(
            backend, conf.get('host', '0.0.0.0'), conf.get('port', 24000),
            conf.get('webhook_path', '/webhook'), web_path)
        await asyncio.Future()
    except asyncio.CancelledError:
        pass
    except Exception as e:
        pdb.set_trace()
        raise
    finally:
        if web_server:
            await web_server.async_close()
        if backend:
            await backend.async_close()
        await asyncio.sleep(0.5)


def _create_parser():
    parser = argparse.ArgumentParser(prog='hatter')
    parser.add_argument(
        '--web-path', default=None, metavar='path', dest='web_path',
        help="web ui directory path")

    named_arguments = parser.add_argument_group('required named arguments')
    named_arguments.add_argument(
        '--conf', required=True, metavar='path', dest='conf_path',
        help='configuration path')

    return parser


def _run_until_complete_without_interrupt(future):
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


if __name__ == '__main__':
    sys.exit(main())
