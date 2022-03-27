from pathlib import Path

from hat import json
from hat.doit import common
from hat.doit.py import (build_wheel,
                         run_flake8)


__all__ = ['task_clean_all',
           'task_wheel',
           'task_check',
           'task_json_schema_repo',
           'task_scss']


build_dir = Path('build')
src_py_dir = Path('src_py')
src_scss_dir = Path('src_scss')
schemas_json_dir = Path('schemas_json')

ui_dir = src_py_dir / 'boxhatter/ui'

json_schema_repo_path = src_py_dir / 'boxhatter/json_schema_repo.json'
main_scss_path = src_scss_dir / 'main.scss'
main_css_path = ui_dir / 'main.css'


def task_clean_all():
    """Clean all"""
    return {'actions': [(common.rm_rf, [build_dir,
                                        json_schema_repo_path,
                                        main_css_path])]}


def task_wheel():
    """Build wheel"""

    def build():
        build_wheel(
            src_dir=src_py_dir,
            dst_dir=build_dir,
            name='boxhatter',
            description='Continuous integration server/executor',
            url='https://github.com/bozokopic/boxhatter',
            license=common.License.GPL3,
            packages=['boxhatter'],
            console_scripts=['boxhatter = boxhatter.main:main'])

    return {'actions': [build],
            'task_dep': ['json_schema_repo',
                         'scss']}


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


def task_scss():
    """Build SCSS"""
    return {'actions': [(common.mkdir_p, [main_css_path.parent]),
                        (f'sass --no-source-map '
                         f'{main_scss_path} {main_css_path}')],
            'targets': [main_css_path]}
