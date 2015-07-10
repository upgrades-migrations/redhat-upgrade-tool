# boot - bootloader config modification code
#
# Copyright (C) 2012 Red Hat Inc.
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
# Author: Will Woods <wwoods@redhat.com>

from .util import check_output, check_call, PIPE, Popen, CalledProcessError
from shutil import copyfileobj

import logging
log = logging.getLogger(__package__+".boot")

kernelprefix = "/boot/vmlinuz-"

def kernelver(kernel):
    if kernel.startswith(kernelprefix):
        return kernel.split(kernelprefix,1)[1]
    else:
        raise ValueError("kernel name must start with '%s'" % kernelprefix)

def add_entry(kernel, initrd, banner=None, kargs=[], makedefault=True, remove_kargs=[]):
    cmd = ["new-kernel-pkg", "--initrdfile", initrd]
    if banner:
        cmd += ["--banner", banner]
    if kargs:
        cmd += ["--kernel-args", " ".join(kargs)]
    if makedefault:
        cmd += ["--make-default"]
    cmd += ["--install", kernelver(kernel)]
    output = check_output(cmd)

    if remove_kargs:
        # Update the entry to remove arguments pulled in from the default entry
        cmd = ["new-kernel-pkg", "--remove-args", " ".join(remove_kargs),
                "--update", kernelver(kernel)]
        output += check_output(cmd)

    return output

def remove_entry(kernel):
    cmd = ["new-kernel-pkg", "--remove", kernelver(kernel)]
    return check_output(cmd)

def initramfs_append_files(initramfs, files):
    '''Append the given files to the named initramfs.
       Raises IOError if the files can't be read/written.
       Raises CalledProcessError if cpio returns a non-zero exit code.'''
    if isinstance(files, basestring):
        files = [files]
    filelist = ''.join(f+'\n' for f in files if open(f))
    with open(initramfs, 'ab') as outfd:
        cmd = ["cpio", "-co"]
        cpio = Popen(cmd, stdin=PIPE, stdout=outfd, stderr=PIPE)
        (out, err) = cpio.communicate(input=filelist)
        if cpio.returncode:
            raise CalledProcessError(cpio.returncode, cmd, err)

def initramfs_append_images(initramfs, images):
    '''Append the given images to the named initramfs.
       Raises IOError if the files can't be read/written.'''
    with open(initramfs, 'ab') as outfd:
        for i in images:
            with open(i, 'rb') as infd:
                copyfileobj(infd, outfd)

def need_mdadmconf():
    '''Does this system need /etc/mdadm.conf to boot?'''
    # NOTE: there are probably systems that have mdadm.conf but don't require
    # it to boot, but I don't know how you tell the difference, so...
    try:
        for line in open("/etc/mdadm.conf"):
            line = line.strip()
            if line and not line.startswith("#"):
                # Hey there's actual *data* in here! WE MIGHT NEED THIS!!
                return True
    except IOError:
        pass
    return False

def upgrade_boot_args():
    '''function checks if all boot parameters are fine

       This function will modify the arguments for the current default bootloader
       entry. dracut in RHEL 6 can accept either the old or new bootloader
       arguments, but systemd in RHEL 7 requires the new arguments. This
       function must be called to modify the current bootloader entry, which
       will be used as the template for both the System Upgrade entry and the
       entry created during the kernel upgrade.

       This change is not undone by --resetbootloader.
    '''
    replaced_options = {'rdbreak': 'rd.break', 'rd_DASD_MOD': 'rd.dasd',
                        'rdinitdebug': 'rd.debug', 'rdnetdebug': 'rd.debug',
                        'rdblacklist': 'rd.driver.blacklist', 'rdinsmodpost': 'rd.driver.post',
                        'rdloaddriver': 'rd.driver.pre', 'rdinfo': 'rd.info', 'check': 'rd.live.check',
                        'rdlivedebug': 'rd.live.debug', 'live_dir': 'rd.live.dir',
                        'liveimg': 'rd.live.image', 'overlay': 'rd.live.overlay',
                        'readonly_overlay': 'rd.live.overlay.readonly', 'reset_overlay': 'rd.live.overlay.reset',
                        'live_ram': 'rd.live.ram', 'rdshell': 'rd.shell', 'rd_NO_SPLASH': 'rd.splash',
                        'rdudevdebug': 'rd.udev.debug', 'rdudevinfo': 'rd.udev.info',
                        'KEYMAP': 'vconsole.keymap', 'KEYTABLE': 'vconsole.keymap',
                        'SYSFONT': 'vconsole.font', 'CONTRANS': 'vconsole.font.map',
                        'UNIMAP': 'vconsole.font.unimap', 'UNICODE': 'vconsole.unicode',
                        'EXT_KEYMAP': 'vconsole.keymap.ext', 'LANG': 'rd.locale.LANG'}
    no_options = {'rd_NO_DM': 'rd.dm=0', 'rd_NO_DM': 'rd.dm=0', 'rd_NO_LVM': 'rd.lvm=0',
                  'rd_NO_MD': 'rd.md=0', 'rd_NO_LUKS': 'rd.luks=0', 'rd_NO_CRYPTTAB': 'rd.luks.crypttab=0',
                  'rd_NO_PLYMOUTH': 'rd.plymouth=0', 'rd_NO_MDADMCONF': 'rd.md.conf=0',
                  'rd_NO_LVMCONF': 'rd.lvm.conf', 'rd_NO_MDIMSM': 'rd.md.imsm=0', 'rd_NO_MULTIPATH': 'rd.multipath=0',
                  'rd_NO_ZFCPCONF': 'rd.zfcp.conf=0', 'rd_NO_FSTAB': 'rd.fstab=0',
                  'iscsi_firmware': 'rd.iscsi.firmware=0'}
    translate_options = ['rd_NFS_DOMAIN', 'rd_LVM_SNAPHOST', 'rd_LVM_SNAPSIZE', 'rd_LVM_VG',
                         'rd_LUKS_KEYPATH', 'rd_LUKS_UUID', 'rd_LVM_LV', 'rd_retry',
                         'rd_ZNET', 'rd_ZFCP', 'rd_CCW', 'rd_DM_UUID', 'rd_MD_UUID',
                         'rd_LUKS_KEYDEV_UUID',
                         ]
    iscsi_options = ['iscsi_initiator', 'iscsi_target_name', 'iscsi_target_ip', 'iscsi_target_port',
                     'iscsi_target_group', 'iscsi_username',
                     'iscsi_password', 'iscsi_in_username', 'iscsi_in_password']

    orig_args = []
    new_args = []

    # Use grubby to get the current list of arguments
    kernel = check_output(['grubby', '--default-kernel']).strip()
    kinfo = check_output(['grubby', '--info=%s' % kernel]).split('\n')

    # Look for the line starting with args=, remove the args= and the quotes,
    # split the line into a list.
    for line in kinfo:
        if line.startswith('args='):
            orig_args = line[6:-1].split()
            break

    for arg in orig_args:
        arg_name = arg.split('=')[0]

        if arg_name in replaced_options:
            arg = arg.replace(arg_name, replaced_options[arg_name])

        if arg_name in no_options:
            arg = arg.replace(arg_name, no_options[arg_name])

        if arg_name in translate_options:
            arg = arg.replace(arg_name, arg_name.replace('_', '.').lower())

        if arg_name in iscsi_options:
            arg = 'rd.' + arg.replace(arg_name, '_', '.')

        new_args.append(arg)

    # Use new-kernel-pkg to remove the old list of arguments and add back the new one
    log.info("Upgrading kernel args for %s", kernel)
    log.debug("Old args: %s", orig_args)
    log.debug("New args: %s", new_args)
    check_call(['new-kernel-pkg', '--remove-args', ' '.join(orig_args),
        '--update', kernelver(kernel)])
    check_call(['new-kernel-pkg', '--kernel-args', ' '.join(new_args),
        '--update', kernelver(kernel)])
