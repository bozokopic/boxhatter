import sys
import asyncio
import argparse
import pdb
import yaml
import logging.config
import atexit
import pkg_resources
import pathlib

import hatter.json_validator
from hatter import util
from hatter.backend import Backend
from hatter.server import create_web_server


def main():
    args = _create_parser().parse_args()

    with open(args.conf, encoding='utf-8') as conf_file:
        conf = yaml.safe_load(conf_file)
    hatter.json_validator.validate(conf, 'hatter://server.yaml#')

    if 'log' in conf:
        logging.config.dictConfig(conf['log'])

    if args.web_path:
        web_path = args.web_path
    else:
        atexit.register(pkg_resources.cleanup_resources)
        web_path = pkg_resources.resource_filename('hatter', 'web')

    util.run_until_complete_without_interrupt(async_main(conf, web_path))


async def async_main(conf, web_path):
    backend = None
    web_server = None
    try:
        backend = Backend(pathlib.Path(conf.get('db_path', 'hatter.db')))
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
        '-c', '--conf', required=True, metavar='path', dest='conf',
        help='configuration path')

    return parser


if __name__ == '__main__':
    sys.exit(main())
