import os
from subprocess import CalledProcessError
from ConfigParser import RawConfigParser, NoOptionError
from .util import check_call


class SnapshotMetaConfig(object):

    def __init__(self, path):
        self.path = path
        self._config = RawConfigParser()
        self._config.read(path)

    def list(self):
        return [(
            self._config.get(section, "origin_lv"),
            self._config.get(section, "name"),
            self._config.get(section, "size"),
        ) for section in self._config.sections()]

    def save_all(self, snapshots):
        # TODO: clean in case of failure: file and snapshots
        for snapshot in snapshots:
            if not isinstance(snapshot, Snapshot):
                raise Exception("Invalid snapshot type!")
            self._config.add_section(snapshot.lv)
            for param in ("origin_lv", "name", "size"):
                self._config.set(snapshot.lv, param, getattr(snapshot, param))
            with open(self.path, "wb") as meta_file:
                self._config.write(meta_file)

    def clean(self):
        for section in self._config.sections():
            self._config.remove_section(section)
        with open(self.path, "wb") as meta_file:
            self._config.write(meta_file)


class LVM(object):
    snapshots = []

    def __init__(self, root_snap_args=None, snap_args=None, conf_path=None):
        self.metadata_conf = SnapshotMetaConfig(conf_path)
        meta_snapshots = self.metadata_conf.list()

        root_snap_args = [] if root_snap_args is None else root_snap_args
        snap_args = [] if snap_args is None else snap_args

        root_lv = None
        if root_snap_args:
            root_lv, _, _ = self.get_snapshot_opt(root_snap_args)

        for args in list(snap_args) + meta_snapshots:
            # TODO: validate if lv path exists and it is lv
            origin_lv, name, size = self.get_snapshot_opt(args)
            is_root = True if root_lv == origin_lv else False
            self.snapshots.append(Snapshot(origin_lv, name, size, is_root))

    @property
    def snapshots_len(self):
        return len(self.snapshots)

    @staticmethod
    def get_snapshot_opt(opt):
        if isinstance(opt, (list, tuple)) and len(opt) == 3:
            origin_lv, name, size = opt
            return (origin_lv, name, size)
        raise Exception("Invalid snapshot params!")

    # TODO: this function has to be more generic
    # we need to have possibility to get snapshot by
    # path, name
    def get_root_snapshot(self):
        for snapshot in self.snapshots:
            return snapshot if snapshot.root else None

    def create_snapshots(self):
        # TODO: add support if snapshots already exists
        # right now metadata file will be erased
        for index, snapshot in enumerate(self.snapshots):
            if snapshot.exists:
                continue
            if not snapshot.create():
                self.remove_snapshots(index)
                return False
        self.metadata_conf.save_all(self.snapshots)
        return True

    def remove_snapshots(self, to_index=None):
        for snapshot in self.snapshots[:to_index]:
            # TODO: check flag if exists later
            # after when lv path will be validated
            if not snapshot.remove():
                return False
        self.metadata_conf.clean()
        return True

    def restore_snapshots(self):
        for snapshot in self.snapshots:
            snapshot.merge()
        self.metadata_conf.clean()


class Snapshot(object):  # TODO: add metaclass with id to avoid duplication?
    exists = False

    def __init__(self, origin_lv, name=None, size=None, root=False):
        self.origin_lv = origin_lv
        self.name = name
        self.size = size
        self.root = root

    def __repr__(self):
        return self.lv

    @property
    def lv(self):
        return os.path.join(os.path.split(self.origin_lv)[0], self.name)

    def create(self):
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
        cmd = ["lvremove", "-f", self.lv]
        try:
            check_call(cmd)
        except CalledProcessError:
            return False
        else:
            self.exists = False
            return True

    def merge(self):
        cmd = ["lvconvert", "--merge", self.lv]
        try:
            check_call(cmd)
        except CalledProcessError:
            return False
        else:
            self.exists = False
            return True

