'''
This is the fastest rollback implementation,
this script shouldn't be here and should be as standalone tool -
implemented like that due to lack of time :(
'''

import os
import subprocess

from . import rhel6_profile, snapshot_metadata_file
from .snapshot import LVM
from .bootloader import boom_cleanup, restore_boot


if __name__ == '__main__':
    try:
        lvm = LVM(conf_path=snapshot_metadata_file)
        lvm.restore_snapshots()
    except Exception:
        print "Error: unable to restore snapshots"
        raise SystemExit(1)

    # TODO: add boom binary to RHEL7
    # boom_cleanup(rhel6_profile)
    try:
        with open("/boot/rollback/.active-kernel") as f_active_kernel:
            active_kernel = f_active_kernel.read()
            restore_boot(active_kernel)

            with open("/boot/rollback/.all-kernels") as f_all_kernels:
                all_kernels = f_all_kernels.read()
                all_kernels = all_kernels.split('\n')
                for kernel in all_kernels:
                    if active_kernel in kernel:
                        continue
                    subprocess.call(["grubby", "--grub", "--remove-kernel", kernel.replace('kernel', '/boot/vmlinuz')])
    except Exception:
        print "Error: unable to restore boot config"
        raise SystemExit(1)

    os.system("reboot")
