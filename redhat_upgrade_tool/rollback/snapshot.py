import os
from subprocess import CalledProcessError, call
from ConfigParser import RawConfigParser, DuplicateSectionError

try:
    from redhat_upgrade_tool.util import check_call
except ImportError:
    def check_call(*popenargs, **kwargs):
        retcode = call(*popenargs, **kwargs)
        if retcode:
            cmd = kwargs.get("args")
            if cmd is None:
                cmd = popenargs[0]
            raise CalledProcessError(retcode, cmd)
        return 0


# this is not Red Hat Upgrade tool style
# but we have to fix exception handling
# we should avoid raising SystemExit(1) everywhere
class BaseSnapshotError(Exception):
    pass


class SnapshotError(BaseSnapshotError):
    pass


class SnapshotMetaConfig(object):

    def __init__(self, path):
        self.path = path
        self._config = RawConfigParser()
        self._config.read(path)

    def list(self):
        return [(
            self._config.get(section, "origin_lv"),
            self._config.get(section, "name"),
            self._config.get(section, "size")
        ) for section in self._config.sections()]

    def save_all(self, snapshots):
        for snapshot in snapshots:
            if not isinstance(snapshot, Snapshot):
                raise TypeError("Invalid snapshot type!")
            try:
                self._config.add_section(snapshot.lv)
            except DuplicateSectionError:
                # allow to override section
                pass
            for param in ("origin_lv", "name", "size"):
                self._config.set(snapshot.lv, param, getattr(snapshot, param))
            with open(self.path, "wb") as meta_file:
                self._config.write(meta_file)

    def remove_all(self, sections=None):
        if sections is None:
            sections = self._config.sections()
        for section in sections:
            self._config.remove_section(section)
        with open(self.path, "wb") as meta_file:
            self._config.write(meta_file)


class LVM(object):
    snapshots = {}

    def __init__(self, root_snap_args=None, snap_args=None, conf_path=None):
        root_snap_args = [] if root_snap_args is None else root_snap_args
        snap_args = [] if snap_args is None else snap_args

        sections_to_remove = []
        self.metadata_conf = SnapshotMetaConfig(conf_path)

        for origin_lv, name, size in self.metadata_conf.list():
            snapshot = Snapshot(origin_lv, name, size, exists=True)
            if os.path.exists(snapshot.full_path):
                self._add_snapshot(snapshot)
            else:
                sections_to_remove.append(snapshot.lv)
        # if there is snapshot section without existing snapshot then we have to remove it from file
        if sections_to_remove:
            self.metadata_conf.remove_all(sections_to_remove)

        root_lv = None
        if root_snap_args:
            root_lv, _, _ = self.get_snapshot_opt(root_snap_args)

        for args in list(snap_args):
            origin_lv, name, size = self.get_snapshot_opt(args)
            is_root = True if root_lv == origin_lv else False
            self._add_snapshot(Snapshot(origin_lv, name, size, is_root))

    def _add_snapshot(self, obj):
        lv = repr(obj)
        if lv not in self.snapshots:
            self.snapshots[lv] = obj
        # it's possible to indicate new root partition
        # obj == self.snapshots[lv] is checking only origin_lv, name and size without root
        elif lv in self.snapshots and obj == self.snapshots[lv]:
            obj.exists = True
            self.snapshots[lv] = obj
        else:
            raise SnapshotError(
                "Snapshot %s already exists with different parameters, run --clean-snapshots first" % lv
            )

    @property
    def snapshots_len(self):
        return len(self.snapshots)

    @staticmethod
    def get_snapshot_opt(opt):
        if isinstance(opt, (list, tuple)) and len(opt) == 3:
            origin_lv, name, size = opt
            return (origin_lv, name, size)
        raise ValueError("Invalid snapshot params len!")

    # TODO: this function has to be more generic
    # we need to have possibility to get snapshot by
    # path, name
    def get_root_snapshot(self):
        for snapshot in self.snapshots.values():
            if snapshot.root:
                return snapshot

    def create_snapshots(self):
        for snapshot in self.snapshots.values():
            if not snapshot.create():
                self.remove_snapshots()
                return False
        self.metadata_conf.save_all(self.snapshots.values())
        return True

    def remove_snapshots(self):
        for snapshot in self.snapshots.values():
            if not snapshot.remove():
                return False
        self.metadata_conf.remove_all()
        return True

    def restore_snapshots(self):
        for snapshot in self.snapshots.values():
            snapshot.merge()
        self.metadata_conf.remove_all()


class Snapshot(object):

    def __init__(self, origin_lv, name=None, size=None, root=False, exists=False):
        self.origin_lv = origin_lv
        self.name = name
        self.size = size
        self.root = root
        self.exists = exists

    def __repr__(self):
        return self.lv

    def __eq__(self, other):
        if not isinstance(other, Snapshot):
            return False
        return (self.origin_lv, self.name, self.size) == \
                (other.origin_lv, other.name, other.size)

    @property
    def lv(self):
        return os.path.join(os.path.split(self.origin_lv)[0], self.name)

    @property
    def full_path(self):
        if self.lv.startswith('/dev'):
            return self.lv
        return os.path.join('/dev', self.lv)

    def create(self):
        if self.exists:
            return True

        size_opt, size = ("-l", "100%ORIGIN") if not self.size else ("--size", self.size)
        cmd = [
            "lvcreate",
            size_opt, size,
            "--snapshot",
            "--name", self.name,
            self.origin_lv
        ]
        try:
            check_call(cmd)
        except CalledProcessError:
            return False
        else:
            self.exists = True
            return True

    def remove(self):
        if not self.exists:
            return True

        cmd = ["lvremove", "-f", self.lv]
        try:
            check_call(cmd)
        except CalledProcessError:
            return False
        else:
            self.exists = False
            return True

    def merge(self):
        if not self.exists:
            return False

        cmd = ["lvconvert", "--merge", self.lv]
        try:
            check_call(cmd)
        except CalledProcessError:
            return False
        else:
            self.exists = False
            return True
