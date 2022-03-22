from pathlib import Path
import asyncio
import contextlib
import logging.config
import sys
import tempfile
import typing
import subprocess

import appdirs
import click

from hat import aio
from hat import json

from hatter import common


user_config_dir: Path = Path(appdirs.user_config_dir('hatter'))
user_data_dir: Path = Path(appdirs.user_data_dir('hatter'))

default_conf_path: Path = user_config_dir / 'server.yaml'
default_db_path: Path = user_data_dir / 'hatter.db'

ssh_key_path: typing.Optional[Path] = None


@click.group()
@click.option('--log-level',
              default='INFO',
              type=click.Choice(['CRITICAL', 'ERROR', 'WARNING', 'INFO',
                                 'DEBUG', 'NOTSET']),
              help="log level")
@click.option('--ssh-key', default=None, metavar='PATH', type=Path,
              help="private key used for ssh authentication")
def main(log_level: str,
         ssh_key: typing.Optional[Path]):
    global ssh_key_path
    ssh_key_path = ssh_key

    logging.config.dictConfig({
        'version': 1,
        'formatters': {
            'console': {
                'format': "[%(asctime)s %(levelname)s %(name)s] %(message)s"}},
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'formatter': 'console',
                'level': log_level}},
        'root': {
            'level': log_level,
            'handlers': ['console']},
        'disable_existing_loggers': False})


@main.command()
@click.argument('url', required=True)
@click.argument('branch', required=False, default='master')
@click.argument('action', required=False, default='.hatter.yaml')
def execute(url: str,
            branch: str,
            action: str):
    with tempfile.TemporaryDirectory() as repo_dir:
        repo_dir = Path(repo_dir)

        subprocess.run(['git', 'clone', '-q', '--depth', '1',
                        '-b', branch, url, str(repo_dir)],
                       check=True)

        conf = json.decode_file(repo_dir / '.hatter.yaml')
        common.json_schema_repo.validate('hatter://action.yaml#', conf)

        image = conf['image']
        command = conf['command']
        subprocess.run(['podman', 'run', '-i', '--rm',
                        '-v', f'{repo_dir}:/hatter',
                        image, '/bin/sh'],
                       input=f'set -e\ncd /hatter\n{command}\n',
                       encoding='utf-8',
                       check=True)


@main.command()
@click.option('--host', default='0.0.0.0',
              help="listening host name (default 0.0.0.0)")
@click.option('--port', default=24000, type=int,
              help="listening TCP port (default 24000)")
@click.option('--conf', default=default_conf_path, metavar='PATH', type=Path,
              help="configuration defined by hatter://server.yaml# "
                   "(default $XDG_CONFIG_HOME/hatter/server.yaml)")
@click.option('--db', default=default_db_path, metavar='PATH', type=Path,
              help="sqlite database path "
                   "(default $XDG_CONFIG_HOME/hatter/hatter.db")
def server(host: str,
           port: int,
           conf: Path,
           db: Path):
    conf = json.decode_file(conf)
    common.json_schema_repo.validate('hatter://server.yaml#', conf)

    with contextlib.suppress(asyncio.CancelledError):
        aio.run_asyncio(async_server(host, port, conf, db))


async def async_server(host: str,
                       port: int,
                       conf: json.Data,
                       db_path: Path):
    pass


if __name__ == '__main__':
    sys.argv[0] = 'hatter'
    main()
