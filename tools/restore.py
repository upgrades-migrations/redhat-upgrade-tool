#!/usr/bin/env python

"""
Simple PoC script to restore a snapshot taken with RUT.
"""

import os
import re
import sys
import shutil
import argparse
import platform
from subprocess import check_call


def rename_files():
    release = platform.release()
    formats = [
        "initramfs-{0}.img",
        "vmlinuz-{0}",
        "System.map-{0}",
        "symvers-{0}.gz",
        "config-{0}",
    ]
    for fmt in formats:
        src = os.path.join("/boot", fmt.format("snapshot"))
        dst = os.path.join("/boot", fmt.format(release))
        shutil.copy2(src, dst)


def change_boot_entry(snap_lv, root_lv):
    GRUB_CFG = "/boot/grub/menu.lst"
    with open(GRUB_CFG, "r") as fd:
        lines = fd.read()
    with open(GRUB_CFG, "a") as fd:
        pattern = r"#--- RUT_Grub1_BEGIN ---(.+?)#--- RUT_Grub1_END ---"
        regex = re.compile(pattern, re.DOTALL)
        entries = [x.strip() for x in regex.findall(lines) if x.strip()]
        if not entries:
            return False
        for entry in entries:
            final = "\n#--- RUT_Restored_Grub1_BEGIN ---\n"
            final += re.sub(r"snapshot", platform.release(), entry)
            final = re.sub(snap_lv, root_lv, final)
            final = final.replace("RHEL 6 Snapshot", "RHEL 6 Snapshot restored")
            final += "\n#--- RUT_Restored_Grub1_END ---\n"
            fd.write(final)
    return True


def restore_snapshot(snap_lv):
    cmd = [
        "lvconvert",
        "--merge", snap_lv
    ]
    check_call(cmd)


def errorf(msg):
    sys.stderr.write(msg+'\n')


def main(arguments):
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('-r', '--root-lv', help="Root logical volume", type=str)
    parser.add_argument('-s', '--snapshot-lv', help="Snapshot volume", type=str)
    args = parser.parse_args(arguments)
    rename_files()
    if not change_boot_entry(args.snapshot_lv, args.root_lv):
        errorf("Could not change boot entry")
        return 1
    restore_snapshot(args.snapshot_lv)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
