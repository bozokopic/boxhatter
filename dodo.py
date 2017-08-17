import sys
import os
import shutil
import json
import yaml
import subprocess
from pathlib import Path
from doit.action import CmdAction


sys.path += ['src_py']
os.environ['PYTHONPATH'] = os.path.abspath('src_py')

DOIT_CONFIG = {
    'backend': 'sqlite3',
    'default_tasks': ['dist_build'],
    'verbosity': 2}


# ######################## utility functions #################################

def mkdir_p(*paths):
    for path in paths:
        os.makedirs(str(Path(path)), exist_ok=True)


def rm_rf(*paths):
    for path in paths:
        p = Path(path)
        if not p.exists():
            continue
        if p.is_dir():
            shutil.rmtree(str(p), ignore_errors=True)
        else:
            p.unlink()


def cp_r(src, dest):
    src = Path(src)
    dest = Path(dest)
    if src.is_dir():
        shutil.copytree(str(src), str(dest))
    else:
        shutil.copy2(str(src), str(dest))


# ########################## global tasks ####################################

def task_clean_all():
    """Clean all"""

    return {'actions': [(rm_rf, ['build', 'dist'])],
            'task_dep': ['pyhatter_clean',
                         'jshatter_clean',
                         'docs_clean',
                         'dist_clean']}


def task_gen_all():
    """Generate all"""

    return {'actions': None,
            'task_dep': ['pyhatter_gen',
                         'jshatter_gen']}


def task_check_all():
    """Check all"""

    return {'actions': None,
            'task_dep': ['pyhatter_check']}


# ############################ dist tasks #####################################

def task_dist_clean():
    """Distribution - clean"""

    return {'actions': [(rm_rf, ['dist'])]}


def task_dist_build():
    """Distribution - build (DEFAULT)"""

    def generate_setup_py():
        with open('dist/setup.py', 'w', encoding='utf-8') as f:
            f.write('\n')

    return {'actions': [(rm_rf, ['dist']),
                        (cp_r, ['build/pyhatter', 'dist']),
                        (cp_r, ['build/jshatter', 'dist/hatter/web']),
                        generate_setup_py],
            'task_dep': [
                'gen_all',
                'pyhatter_build',
                'jshatter_build']}


# ########################## pyhatter tasks ###################################

def task_pyhatter_clean():
    """PyHatter - clean"""

    return {'actions': [(rm_rf, ['build/pyhatter',
                                 'src_py/hatter/json_validator.py'])]}


def task_pyhatter_build():
    """PyHatter - build"""

    generated_files = {Path('src_py/hatter/json_validator.py')}

    def compile(src_path, dst_path):
        mkdir_p(dst_path.parent)
        # if src_path.suffix == '.py':
        #     py_compile.compile(src_path, dst_path.with_suffix('.pyc'),
        #                        doraise=True)
        # else:
        #     cp_r(src_path, dst_path)
        cp_r(src_path, dst_path)

    def create_subtask(src_path):
        dst_path = Path('build/pyhatter') / src_path.relative_to('src_py')
        return {'name': str(src_path),
                'actions': [(compile, [src_path, dst_path])],
                'file_dep': [src_path],
                'targets': [dst_path]}

    for src_path in generated_files:
        yield create_subtask(src_path)

    for dirpath, dirnames, filenames in os.walk('src_py'):
        if '__pycache__' in dirnames:
            dirnames.remove('__pycache__')
        for i in filenames:
            src_path = Path(dirpath) / i
            if src_path not in generated_files:
                yield create_subtask(src_path)


def task_pyhatter_check():
    """PyHatter - run flake8"""

    return {'actions': [CmdAction('python -m flake8 .', cwd='src_py')]}


def task_pyhatter_gen():
    """PyHatter - generate additional python modules"""

    return {'actions': None,
            'task_dep': ['pyhatter_gen_json_validator']}


def task_pyhatter_gen_json_validator():
    """PyHatter - generate json validator"""

    schema_files = list(Path('schemas_json').glob('**/*.yaml'))
    output_file = Path('src_py/hatter/json_validator.py')

    def parse_schemas():
        schemas = {}
        for schema_file in schema_files:
            with open(schema_file, encoding='utf-8') as f:
                data = yaml.safe_load(f)
                if data['id'] in schemas:
                    raise Exception("duplicate schema id " + data['id'])
                schemas[data['id']] = data
        return schemas

    def generate_output():
        schemas = parse_schemas()
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(
                '# pylint: skip-file\n'
                'import jsonschema\n\n\n'
                '_schemas = ' + repr(schemas) + '  # NOQA\n\n\n'
                'def validate(data, schema_id):\n'
                '    """ Validate data with JSON schema\n\n'
                '    Args:\n'
                '       data: validated data\n'
                '       schema_id (str): JSON schema identificator\n\n'
                '    Raises:\n'
                '       Exception: validation fails\n\n'
                '    """\n'
                '    base_uri = schema_id.split("#")[0] + "#"\n'
                '    fragment = schema_id.split("#")[1] if "#" in schema_id else ""\n'  # NOQA
                '    resolver = jsonschema.RefResolver(\n'
                '        base_uri=base_uri,\n'
                '        referrer=_schemas[base_uri],\n'
                '        handlers={"hat": lambda x: _schemas[x + "#"]})\n'
                '    jsonschema.validate(\n'
                '        instance=data,\n'
                '        schema=resolver.resolve_fragment(resolver.referrer, fragment),\n'  # NOQA
                '        resolver=resolver)\n')

    return {'actions': [generate_output],
            'file_dep': schema_files,
            'targets': [output_file]}


# ########################## jshatter tasks ###################################

def task_jshatter_clean():
    """JsHatter - clean"""

    return {'actions': [(rm_rf, ['build/jshatter',
                                 'src_js/hatter/validator.js'])]}


def task_jshatter_install_deps():
    """JsHatter - install dependencies"""

    def patch():
        subprocess.Popen(['patch', '-r', '/dev/null', '--forward', '-p0',
                          '-i', 'node_modules.patch'],
                         stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL).wait()

    return {'actions': ['yarn install',
                        patch]}


def task_jshatter_remove_deps():
    """JsHatter - remove dependencies"""

    return {'actions': [(rm_rf, ['node_modules', 'yarn.lock'])]}


def task_jshatter_gen():
    """JsHatter - generate additional JavaScript modules"""

    return {'actions': None,
            'task_dep': ['jshatter_gen_validator']}


def task_jshatter_gen_validator():
    """JsHatter - generate json validator"""

    schema_files = list(Path('schemas_json').glob('**/*.yaml'))
    output_file = Path('src_js/hatter/validator.js')

    def parse_schemas():
        for schema_file in schema_files:
            with open(schema_file, encoding='utf-8') as f:
                yield yaml.safe_load(f)

    def generate_output():
        schemas_json = json.dumps(list(parse_schemas()), indent=4)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(
                'import tv4 from "tv4";\n\n\n' +
                schemas_json + '.forEach(i => tv4.addSchema(i.id, i));\n\n\n' +
                'export function validate(data, schemaId) {\n' +
                '    return tv4.validate(data, tv4.getSchema(schemaId));\n' +
                '}\n')

    return {'actions': [generate_output],
            'file_dep': schema_files,
            'targets': [output_file]}


def task_jshatter_build():
    """JsHatter - build"""

    return {'actions': ['yarn run build'],
            'task_dep': ['jshatter_install_deps', 'jshatter_gen']}


def task_jshatter_watch():
    """JsHatter - build on change"""

    return {'actions': ['yarn run watch'],
            'task_dep': ['jshatter_install_deps', 'jshatter_gen']}


# ############################ docs tasks #####################################

def task_docs_clean():
    """Docs - clean"""

    return {'actions': [(rm_rf, ['build/docs'])]}


def task_docs_build():
    """Docs - build documentation"""

    def build_html(src, dest):
        mkdir_p(Path(dest).parent)
        subprocess.Popen([
            'sphinx-build', '-q', '-b', 'html',
            str(Path(src)), str(Path(dest))]).wait()

    return {'actions': [(build_html, ['docs', 'build/docs'])]}
