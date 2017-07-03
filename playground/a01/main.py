import libvirt
import sys
import time
import io
import git
import os
import shutil
import pathlib
import tempfile
import paramiko.client
import paramiko.rsakey


private_key_str = """-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEA9t4sSxeHa8A0TwMOzD9M9OITtcbl3rki/QfBLIFBkKlP24Tx
BOH5dRfWq0LC7j1+ViDUyBEuPw513ADxuwUhpLbhelkDM7rrmobXvKfYfKlK6mtn
RA2tFSeJNmWO7Cz3VYR3JWUgG5TGowXWHRx42MP7fzmbWKd2HSVUUmKVONb98YjW
nZFTmBaV53lHfVLCKitxsToFL0uGzqFSMt27BK9GDaCA159zC4G7YqjiqxkqA5UY
x2IbMFKMd7eAKw/yCdBRuCWGYFvjPlHj1m4zCHZsfFQ5fYrO9NFd2ieYxQBgSfJ+
cDSmiaXXWWfooaG0h2UKMkrqU0YmHGOA2c/xJwIDAQABAoIBAE0Q4Iz0pG7ryqib
0MPMQw7zgKmvlNUpwJVzFUf6deheIrLp1n/qt4BpV7eRGN9czRLAHwzx6BkBP6PV
m6EBohYUjWEvZoOAp8pOrAyV7UxFYUC7FLq29kBzXi9gFvT9uJy2xKck4ZgaosQD
r2rZF5S74cg+yJMte/7vR1qMsf7S6eyrDVMQGP6c0apMT1GxmcAHx9T71ePoYnD2
faUzr+lVnTLGB6wv1cyaF/Nrt/leskBJ0qmKfkWMRc2uPPPDIvGW39z9OIoPqlEr
4RKqwvyqRzh0uQ/4tpZzMQTfQQSzQ3B9gxCyox7Fc8z/KOSVHzbFso9FCjidCtxR
054KmqkCgYEA/r1tdovJzv7AYJeeEV81VFCwtxIg2T04JhhfYiGg/MSSp4Jc05UM
ivVn9VIyjj9kP0mFTSH/4zLFpo9jp7a/HTfqOK6fIT0p8bQ/PJ8ZZ7cQN1MsV7bh
YaXaUF8Oh/yidnZC3dH1ByVrvZC8DolGlpLAvl8i66kUXGvHvnuYNB0CgYEA+BbG
84ge1O9aLxEKzW9soTglFJREMT3jMvK7oUPvYy6JhjoKbM3CnkFSQx+k+QA5wgKf
Z+bWGjWZ3paOP1wgmRl/3/ST08W79I6WaQVBx28DiGypyJ3V0/lkfxvsAhsPhM0n
qya+ASYuYa1OZR2sdykyYA74+lor8DzEwIfB7xMCgYEA9516QbkvuZ23siyu4YQC
eqrUm59rfr8bTSxzyxeVPR52z4zQXnqLbqeNHdGAgvTrpPj6MjfSXC6GIZlP7T6e
FvC7I83ZsJ2bn+7taSfdsgsoIB8hA0IpYpms1GMR5O2VnkDmTmhAHWoqiGGf6yFV
FBgicupXL2ty90NtLaNGF6ECgYAcvE6pEKA5m8u/XeL5bqmPdvhcjNvlNDznvtPa
1wqYW2CUio6Akci0Ge7UVYr/SHZoMXOTTlqISKMc9CVf02T3Nsvn/eVNhz7BEe78
FR7MYeBv4d48nYOR/PYV/v70M3w1rqmkmmUxruF6cN9+uNQsLTpng/R00xL5zaAg
iNj+vwKBgQCbPS90lQ+d3YSB0W5kdBigTfgMASwFiENXHEPReTTDi73y9AQL8yh7
fhwegAxBuKYUMqUh/yjE/lWE9j+TjLufPOLq3K0C+xoOQExuZ7+xEg9SjIju+Fj5
iebkM6IzOZtiCNZXEQvJiHj6aTM6wTy8OhuLry04ayXvJ6Kmj63lsw==
-----END RSA PRIVATE KEY-----
"""


def main():
    repo_path = 'repository'
    conf = {'domain': 'archlinux',
            'ssh_username': 'root',
            'ssh_key': private_key_str,
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
    pkey = paramiko.rsakey.RSAKey.from_private_key(
        io.StringIO(conf['ssh_key']))
    conn = paramiko.client.SSHClient()
    conn.set_missing_host_key_policy(paramiko.client.AutoAddPolicy)
    connected = False
    for _ in range(10):
        try:
            conn.connect(address, username=conf['ssh_username'], pkey=pkey,
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
