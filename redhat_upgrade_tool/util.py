# util.py - various shared utility functions
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

import os, struct
from shutil import rmtree
from subprocess import Popen, CalledProcessError, PIPE, STDOUT
from pipes import quote as shellquote
from redhat_upgrade_tool import grub_conf_file

import logging
log = logging.getLogger(__package__+".util")

try:
    from ctypes import cdll, c_bool
    selinux = cdll.LoadLibrary("libselinux.so.1")
    is_selinux_enabled = selinux.is_selinux_enabled
    is_selinux_enabled.restype = c_bool
except (ImportError, AttributeError, OSError):
    is_selinux_enabled = lambda: False

def call(*popenargs, **kwargs):
    return Popen(*popenargs, **kwargs).wait()

def check_output(*popenargs, **kwargs):
    if 'stdout' in kwargs:
        raise ValueError('stdout argument not allowed, it will be overridden.')
    process = Popen(stdout=PIPE, *popenargs, **kwargs)
    output, unused_err = process.communicate()
    retcode = process.poll()
    if retcode:
        cmd = kwargs.get("args")
        if cmd is None:
            cmd = popenargs[0]
        raise CalledProcessError(retcode, cmd)
    return output

def check_call(*popenargs, **kwargs):
    retcode = call(*popenargs, **kwargs)
    if retcode:
        cmd = kwargs.get("args")
        if cmd is None:
            cmd = popenargs[0]
        raise CalledProcessError(retcode, cmd)
    return 0

def listdir(d):
    for f in os.listdir(d):
        yield os.path.join(d, f)

def rlistdir(d):
    for root, dirs, files in os.walk(d):
        for f in files:
            yield os.path.join(root, f)

def mkdir_p(d):
    try:
        os.makedirs(d)
    except OSError as e:
        if e.errno != 17:
            raise

def rm_f(f, rm=os.remove):
    if not os.path.lexists(f):
        return
    try:
        rm(f)
    except (IOError, OSError) as e:
        log.warn("failed to remove %s: %s", f, str(e))

def rm_rf(d):
    if os.path.isdir(d):
        rm_f(d, rm=rmtree)
    else:
        rm_f(d)

def kernelver(filename):
    '''read the version number out of a vmlinuz file.'''
    # this algorithm came from /usr/share/magic
    with open(filename) as f:
        f.seek(514)
        if f.read(4) != 'HdrS':
            return None
        f.seek(526)
        (offset,) = struct.unpack("<H", f.read(2))
        f.seek(offset+0x200)
        buf = f.read(256)
    uname, nul, rest = buf.partition('\0')
    version, spc, rest = uname.partition(' ')
    return version

def df(mnt, reserved=False):
    s = os.statvfs(mnt)
    return s.f_bsize * (s.f_bfree if reserved else s.f_bavail)

def hrsize(size, si=False, use_ib=False):
    powers = 'KMGTPEZY'
    multiple = 1000 if si else 1024
    if si:       suffix = 'B'
    elif use_ib: suffix = 'iB'
    else:        suffix = ''
    size = float(size)
    for p in powers:
        size /= multiple
        if size < multiple:
            if p in 'KM': # don't bother with sub-MB precision
                return "%u%s%s" % (int(size)+1, p, suffix)
            else:
                return "%.1f%s%s" % (size, p, suffix)


def check_grub_conf_file():
    '''function checks if all boot parameters are fine'''
    content = None
    if not os.path.exists(grub_conf_file):
        return
    with open(grub_conf_file) as f:
        content = f.read()
    if not content:
        return
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
                        'EXT_KEYMAP': 'vconsole.keymap.ext'}
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
    for key, value in replaced_options.iteritems():
        content = content.replace(key, value)
    for key, value in no_options.iteritems():
        content = content.replace(key, value)
    for translate in translate_options:
        content = content.replace(translate, translate.replace('_', '.').lower())

    for iscsi in iscsi_options:
        content = content.replace(iscsi, 'rd.' + iscsi.replace('_', '.'))

    with open(grub_conf_file, mode='w') as f:
        f.write(content)
