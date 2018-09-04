import os
import re
import shutil
import platform
from subprocess import CalledProcessError, call

try:
    from redhat_upgrade_tool import grub_conf_file
    from redhat_upgrade_tool.util import check_call
except ImportError:
    grub_conf_file = "/boot/grub/grub.conf"
    def check_call(*popenargs, **kwargs):
        retcode = call(*popenargs, **kwargs)
        if retcode:
            cmd = kwargs.get("args")
            if cmd is None:
                cmd = popenargs[0]
            raise CalledProcessError(retcode, cmd)
        return 0


_SNAP_BOOT_FILES = [
    "initramfs-{0}.img",
    "vmlinuz-{0}",
    "System.map-{0}",
    "symvers-{0}.gz",
    "config-{0}",
]

_BOOM_UTIL_PATH = "/usr/libexec/boom"

def create_boot_entry(title, os_profile, root_lv):
    cmd = [
        _BOOM_UTIL_PATH, "create",
        "--profile", os_profile,
        "--title", title,
        "--root-lv", root_lv
    ]
    try:
        check_call(cmd)
    except CalledProcessError:
        return False
    return True


def boom_cleanup(os_profile):
    cmd = [
        _BOOM_UTIL_PATH, "delete",
        "--profile", os_profile
    ]
    try:
        check_call(cmd)
    except CalledProcessError:
        return False
    return True


def backup_boot_files():
    release = platform.release()
    for fmt in _SNAP_BOOT_FILES:
        src = os.path.join("/boot", fmt.format(release))
        dst = os.path.join("/boot", fmt.format("snapshot"))
        shutil.copy2(src, dst)
    # back up grub config file
    shutil.copy2(grub_conf_file, "%s.preupg" % grub_conf_file)


def change_boot_entry():
    with open(grub_conf_file, "r") as fd:
        lines = fd.read()
    with open(grub_conf_file, "a") as fd:
        pattern = r"#--- BOOM_Grub1_BEGIN ---(.+?)#--- BOOM_Grub1_END ---"
        regex = re.compile(pattern, re.DOTALL)
        entries = [x.strip() for x in regex.findall(lines) if x.strip()]
        if not entries:
            return False
        fd.write("\ntitle RUT Snapshots\n")
        for entry in entries:
            fd.write("\n#--- RUT_Grub1_BEGIN ---\n")
            fd.write(re.sub(platform.release(), "snapshot", entry))
            fd.write("\n#--- RUT_Grub1_END ---\n")
    return True


def restore_boot(release=platform.release()):
    for fmt in _SNAP_BOOT_FILES:
        src = os.path.join("/boot", fmt.format("snapshot"))
        dst = os.path.join("/boot", fmt.format(release))
        shutil.move(src, dst)
    return restore_grub_conf()


def clean_snapshot_boot_files():
    for fmt in _SNAP_BOOT_FILES:
        path = os.path.join("/boot", fmt.format("snapshot"))
        if os.path.isfile(path):
            os.remove(path)


def restore_grub_conf():
    backup_file = "%s.preupg" % grub_conf_file
    if os.path.isfile(backup_file):
        shutil.move(backup_file, grub_conf_file)
        return True
    return False
