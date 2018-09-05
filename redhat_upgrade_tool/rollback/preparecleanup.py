# preparecleanup.py
#
# Copyright (C) 2018 Red Hat Inc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Author: Jakub Mazanek <jmazanek@redhat.com>

import json
import os
import shutil
import subprocess
import platform
from redhat_upgrade_tool.util import mkdir_p
from redhat_upgrade_tool.rollback import rollback_dir, snap_boot_files_file
from redhat_upgrade_tool.rollback import active_kernel_file, all_kernels_file, target_kernel_file
from redhat_upgrade_tool.rollback.bootloader import _SNAP_BOOT_FILES


def create_cleanup_script():
    rollback_path = os.path.dirname(os.path.abspath(__file__))
    if os.path.exists(rollback_dir):
        shutil.rmtree(rollback_dir)
    shutil.copytree(rollback_path, rollback_dir)

    with open(active_kernel_file, 'w') as active_kernel:
        active_kernel.write(platform.release())

    with open(all_kernels_file, 'w') as all_kernels:
        all_kernels.write(subprocess.Popen(["rpm", "-qa", "kernel"], stdout=subprocess.PIPE).communicate()[0])

    script_path = os.path.join(rollback_dir, 'do_rollback')
    with open(script_path, 'wb') as script_file:
        script_file.write("#!/bin/bash\ncd /boot && python -m rollback.system_restore\n")
    os.chmod(script_path, 0o774)

    script_path = os.path.join(rollback_dir, 'do_cleanup')
    with open(script_path, 'wb') as script_file:
        script_file.write("#!/bin/bash\ncd /boot && python -m rollback.cleanup_script\n")
    os.chmod(script_path, 0o774)

    dump_snapshot_boot_files()


def dump_target_kernelver(kv):
    # kv = kernel version
    with open(target_kernel_file, 'w') as target_kernel:
        target_kernel.write(kv)


def dump_snapshot_boot_files():
    _SNAP_BOOT_PATHS = []
    for fmt in _SNAP_BOOT_FILES:
        path = os.path.join("/boot", fmt.format("snapshot"))
        _SNAP_BOOT_PATHS.append(path)
        dump_vars(_SNAP_BOOT_PATHS, snap_boot_files_file)


def dump_vars(variables, out_file):
    with open(out_file, 'w+') as outfile:
        json.dump(variables, outfile)
