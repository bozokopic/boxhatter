import time
import libvirt


class VM:

    def __init__(self, domain_name, uri='qemu:///system', snapshot_name=None,
                 temp_snapshot_name='temp_hatter', address_retry_count=10,
                 address_delay=5):
        self._domain_name = domain_name
        self._uri = uri
        self._snapshot_name = snapshot_name
        self._temp_snapshot_name = temp_snapshot_name
        self._address_retry_count = address_retry_count
        self._address_delay = address_delay
        self._conn = None
        self._domain = None
        self._temp_snapshot = None
        self._address = None

    @property
    def address(self):
        return self._address

    def start(self):
        try:
            self._conn = _libvirt_connect(self._uri)
            self._domain = _libvirt_get_domain(self._conn, self._domain_name)
            if self._domain.isActive():
                self._domain.destroy()
            self._temp_snapshot = _libvirt_create_temp_snapshot(
                self._domain, self._temp_snapshot_name)
            if self._snapshot_name:
                _libvirt_revert_snapshot(self._domain, self._snapshot_name)
            _libvirt_start_domain(self._domain)
            for _ in range(self._address_retry_count):
                self._address = _libvirt_get_address(self._domain)
                if self._address:
                    return
                time.sleep(self._address_delay)
            raise Exception('ip addess not detected')
        except Exception:
            self.stop()
            raise

    def stop(self):
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
