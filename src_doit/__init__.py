from pathlib import Path

from hat import json
from hat.doit import common
from hat.doit.py import (build_wheel,
                         run_flake8)


__all__ = ['task_clean_all',
           'task_wheel',
           'task_check',
           'task_json_schema_repo']


build_dir = Path('build')
src_py_dir = Path('src_py')
schemas_json_dir = Path('schemas_json')

json_schema_repo_path = src_py_dir / 'hatter/json_schema_repo.json'


def task_clean_all():
    """Clean all"""
    return {'actions': [(common.rm_rf, [build_dir,
                                        json_schema_repo_path])]}


def task_wheel():
    """Build wheel"""

    def build():
        build_wheel(
            src_dir=src_py_dir,
            dst_dir=build_dir,
            name='hatter',
            description='Continuous integration server/executor',
            url='https://github.com/bozokopic/hatter',
            license=common.License.GPL3,
            packages=['hatter'],
            console_scripts=['hatter = hatter.main:main'])

    return {'actions': [build],
            'task_dep': ['json_schema_repo']}


def task_check():
    """Check"""
    return {'actions': [(run_flake8, [src_py_dir])]}


def task_json_schema_repo():
    """Generate JSON Schema Repository"""
    src_paths = list(schemas_json_dir.rglob('*.yaml'))

    def generate():
        repo = json.SchemaRepository(*src_paths)
        data = repo.to_json()
        json.encode_file(data, json_schema_repo_path, indent=None)

    return {'actions': [generate],
            'file_dep': src_paths,
            'targets': [json_schema_repo_path]}
