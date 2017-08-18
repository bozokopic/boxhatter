import tempfile
import pathlib
import tarfile
import subprocess
import io
import time
import contextlib
import yaml
import libvirt
import paramiko

import hatter.json_validator


def run(log, repo_path, commit='HEAD', archive_name='hatter_archive'):
    log.info('starting executor for repository {} ({})'.format(repo_path,
                                                               commit))
    t_begin = time.monotonic()
    archive_file_name = archive_name + '.tar.gz'
    with tempfile.TemporaryDirectory() as tempdir:
        archive_path = pathlib.Path(tempdir) / archive_file_name
        log.info('fetching remote repository')
        _git_archive(repo_path, commit, archive_path)
        log.info('loading project configuration')
        conf = _load_conf(archive_path)
        for i in conf:
            log.info('starting virtual machine')
            with contextlib.closing(_VM(i['vm'])) as vm:
                log.info('creating SSH connection')
                with contextlib.closing(_SSH(i['ssh'], vm.address)) as ssh:
                    log.info('transfering repository to virtual machine')
                    ssh.execute('rm -rf {} {}'.format(archive_file_name,
                                                      archive_name))
                    ssh.upload(archive_path, archive_file_name)
                    ssh.execute('mkdir {}'.format(archive_name))
                    ssh.execute('tar xf {} -C {}'.format(archive_file_name,
                                                         archive_name))
                    log.info('executing scripts')
                    for script in i['scripts']:
                        ssh.execute(script, archive_name, log)
    t_end = time.monotonic()
    log.info('executor finished (duration: {}s)'.format(t_end - t_begin))


class _VM:

    def __init__(self, conf):
        self._conn = None
        self._domain = None
        self._temp_snapshot = None
        self._address = None
        try:
            self._conn = _libvirt_connect(conf.get('uri', 'qemu:///system'))
            self._domain = _libvirt_get_domain(self._conn, conf['domain'])
            if self._domain.isActive():
                self._domain.destroy()
            self._temp_snapshot = _libvirt_create_temp_snapshot(
                self._domain, conf.get('temp_snapshot', 'temp_hatter'))
            if 'snapshot' in conf:
                _libvirt_revert_snapshot(self._domain, conf['snapshot'])
            _libvirt_start_domain(self._domain)
            for _ in range(conf('get_address_retry_count', 10)):
                self._address = _libvirt_get_address(self._domain)
                if self._address:
                    return
                time.sleep(conf.get('get_address_delay', 5))
            raise Exception('ip addess not detected')
        except Exception:
            self.close()
            raise

    @property
    def address(self):
        return self._address

    def close(self):
        if self._domain:
            self._domain.destroy()
        if self._domain and self._temp_snapshot:
            self._domain.revertToSnapshot(self._temp_snapshot)
        if self._temp_snapshot:
            self._temp_snapshot.delete()
        if self._conn:
            self._conn.close()
        self._temp_snapshot = None
        self._domain = None
        self._conn = None
        self._address = None


class _SSH:

    def __init__(self, conf, address):
        self._conn = paramiko.SSHClient()
        self._conn.set_missing_host_key_policy(paramiko.AutoAddPolicy)
        for _ in range(conf.get('connect_retry_count', 10)):
            try:
                self._conn.connect(
                    address,
                    username=conf['username'], password=conf['password'],
                    timeout=conf.get('connect_timeout', 1),
                    auth_timeout=conf.get('connect_timeout', 1))
                return
            except Exception as e:
                time.sleep(conf.get('connect_delay', 5))
        raise Exception('could not connect to {}'.format(address))

    def close(self):
        if self._conn:
            self._conn.close()
        self._conn = None

    def upload(self, src_path, dst_path):
        with contextlib.closing(self._conn.open_sftp()) as sftp:
            sftp.put(str(src_path), str(dst_path))

    def execute(self, cmd, cwd='.', log=None):
        if log:
            log.info('executing command: {}'.format(cmd))
        with contextlib.closing(self._conn.invoke_shell()) as shell:
            shell.set_combine_stderr(True)
            shell.exec_command('cd {} && {}'.format(cwd, cmd))
            with contextlib.closing(shell.makefile()) as f:
                data = f.read()
                if log:
                    log.info('command output: {}'.format(data))
            exit_code = shell.recv_exit_status()
            if exit_code > 0:
                raise Exception('command exit code is {}'.format(exit_code))


def _load_conf(archive_path):
    with tarfile.open(archive_path) as archive:
        f = io.TextIOWrapper(archive.extractfile('.hatter.yml'),
                             encoding='utf-8')
        conf = yaml.safe_load(f)
        hatter.json_validator.validate(conf, 'hatter://project.yaml#')
        return conf


def _git_archive(repo_path, commit, output_path):
    result = subprocess.run(
        ['git', 'archive', '--format=tar.gz',
         '--outfile={}'.format(str(output_path)),
         '--remote={}'.format(repo_path),
         commit],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if result.returncode:
        raise Exception("could not archive {} from {}".format(commit,
                                                              repo_path))


def _libvirt_connect(uri):
    conn = libvirt.open(uri)
    if not conn:
        raise Exception('could not open connection to {}'.format(uri))
    return conn


def _libvirt_get_domain(conn, domain_name):
    domain = conn.lookupByName(domain_name)
    if not domain:
        raise Exception('domain {} not available'.format(domain_name))
    return domain


def _libvirt_start_domain(domain):
    if domain.create():
        raise Exception('could not run vm')


def _libvirt_create_temp_snapshot(domain, temp_snapshot_name):
    temp_snapshot = domain.snapshotLookupByName(temp_snapshot_name)
    if temp_snapshot:
        temp_snapshot.delete()
    temp_snapshot = domain.snapshotCreateXML(
        "<domainsnapshot><name>{}</name></domainsnapshot>".format(
            temp_snapshot_name))
    if not temp_snapshot:
        raise Exception('could not create snapshot {}'.format(
            temp_snapshot_name))
    return temp_snapshot


def _libvirt_revert_snapshot(domain, snapshot_name):
    snapshot = domain.snapshotLookupByName(snapshot_name)
    if not snapshot:
        raise Exception('snapshot {} not available'.format(snapshot_name))
    if domain.revertToSnapshot(snapshot):
        raise Exception('could not revert snapshot {}'.format(snapshot_name))


def _libvirt_get_address(domain):
    addresses = domain.interfaceAddresses(0)
    for i in addresses.values():
        for j in i.get('addrs', []):
            return j.get('addr')
