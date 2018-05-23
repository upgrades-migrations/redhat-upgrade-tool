import os

from . import rhel6_profile, snapshot_metadata_file
from .snapshot import LVM
from .bootloader import boom_cleanup, restore_boot


if __name__ == '__main__':
    lvm = LVM(conf_path=snapshot_metadata_file)
    lvm.restore_snapshots()
    boom_cleanup(rhel6_profile)
    restore_boot()
    os.system("reboot")
