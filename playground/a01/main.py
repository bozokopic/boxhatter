import libvirt
import sys
import time
import git
import os
import shutil
import pathlib
import tempfile
import paramiko.client
import paramiko.rsakey


def main():
    repo_path = 'repository'
    conf = {'domain': 'archlinux',
            'ssh_username': 'root',
            'ssh_password': 'archlinux',
            'script': ['pwd',
                       'ls',
                       'cat test.txt']}
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_arch_path = str(
            (pathlib.Path(tmpdir) / 'hatter_archive.tar').absolute())
        init_git_archive(repo_path, repo_arch_path)
        execute_libvirt(conf, repo_arch_path)


def init_git_archive(repo_path, repo_arch_path):
    shutil.rmtree(repo_path, ignore_errors=True)
    os.mkdir(repo_path)
    with open(pathlib.Path(repo_path) / 'test.txt', 'w',
              encoding='utf-8') as f:
        f.write('test123\n')
    g = git.Git(repo_path)
    g.init()
    g.add('.')
    g.commit(m='init')
    g.archive('HEAD', o=repo_arch_path)


def execute_libvirt(conf, repo_arch_path):
    conn = libvirt.open(conf.get('uri', 'qemu:///system'))
    domain = conn.lookupByName(conf['domain'])
    if domain.isActive():
        domain.destroy()
    snapshot_names = domain.snapshotListNames()
    if 'temp_hatter' in snapshot_names:
        domain.snapshotLookupByName('temp_hatter').delete()
    origin_snapshot = domain.snapshotCreateXML(
        "<domainsnapshot><name>temp_hatter</name></domainsnapshot>")
    snapshot_name = conf.get('snapshot')
    if snapshot_name:
        snapshot = domain.snapshotLookupByName(snapshot_name)
        if snapshot:
            domain.revertToSnapshot(snapshot)
    domain.create()
    address = None
    for _ in range(10):
        addresses = domain.interfaceAddresses(0)
        for i in addresses.values():
            for j in i['addrs']:
                address = j['addr']
                break
        if address:
            execute_ssh(conf, address, repo_arch_path)
            break
        time.sleep(1)
    domain.destroy()
    domain.revertToSnapshot(origin_snapshot)
    origin_snapshot.delete()
    conn.close()


def execute_ssh(conf, address, repo_arch_path):
    conn = paramiko.client.SSHClient()
    conn.set_missing_host_key_policy(paramiko.client.AutoAddPolicy)
    connected = False
    for _ in range(10):
        try:
            conn.connect(address, username=conf['ssh_username'],
                         password=conf['ssh_password'],
                         timeout=1, auth_timeout=1)
            connected = True
            break
        except Exception as e:
            time.sleep(5)
    if not connected:
        return
    sftp_conn = conn.open_sftp()
    sftp_conn.put(repo_arch_path, 'hatter_archive.tar')
    sftp_conn.close()
    execute_ssh_cmd(conn, 'rm -rf hatter_archive', '.')
    execute_ssh_cmd(conn, 'mkdir hatter_archive', '.')
    execute_ssh_cmd(conn, 'tar xf hatter_archive.tar -C hatter_archive', '.')
    for cmd in conf['script']:
        print('>> ', cmd)
        stdout, stderr = execute_ssh_cmd(conn, cmd, 'hatter_archive')
        print('>>>> stdout')
        print(stdout, end='')
        print('>>>> stderr')
        print(stderr)
    conn.close()


def execute_ssh_cmd(conn, cmd, cwd):
    _, ssh_stdout, ssh_stderr = conn.exec_command(
        'cd {} && {}'.format(cwd, cmd))
    return ssh_stdout.read().decode('utf-8'), ssh_stderr.read().decode('utf-8')


if __name__ == '__main__':
    sys.exit(main())
