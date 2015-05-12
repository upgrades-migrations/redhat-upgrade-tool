# sysprep.py - utility functions for system prep
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

import os, glob, re
from shutil import copy2
from ConfigParser import ConfigParser, NoOptionError

from . import _
from . import cachedir, packagedir, packagelist, update_img_dir
from . import upgradeconf, upgradelink, upgraderoot
from .media import write_prep_mount
from .util import listdir, mkdir_p, rm_f, rm_rf, is_selinux_enabled, kernelver, check_output, check_call
from .conf import Config
from . import boot

import logging
log = logging.getLogger(__package__+".sysprep")

upgrade_prep_dir = packagedir + "/upgrade-prep"

# Override ConfigParser.write so we can add comments in the right place
class YumRepoParser(ConfigParser):
    # Use this as value to print a comment plus enabled=0
    DISABLE = "REDHAT_UPGRADE_TOOL_DISABLE"

    def write(self, fp):
        for section in self.sections():
            fp.write("[%s]\n" % section)
            for (key, value) in self.items(section):
                if key != "__name__":
                    if value == self.DISABLE:
                        fp.write("# disabled by redhat-upgrade-tool\nenabled = 0\n")
                    else:
                        fp.write("%s=%s\n" % (key, str(value).replace('\n', '\n\t')))
            fp.write("\n")

def setup_cleanup_post():
    '''Set a flag in upgrade.conf to be read by preupgrade-assistant,
       signalling it to cleanup old packages in the post scripts.'''

    with Config(upgradeconf) as conf:
        conf.set('postupgrade', 'cleanup', 'True')

def link_pkgs(pkgs):
    '''link the named pkgs into packagedir, overwriting existing files.
       also removes any .rpm files in packagedir that aren't in pkgs.
       finally, write a list of packages to upgrade and a list of dirs
       to clean up after successful upgrade.'''

    log.info("linking required packages into packagedir")
    log.info("packagedir = %s", packagedir)
    mkdir_p(packagedir)

    pkgbasenames = set()
    for pkg in pkgs:
        pkgpath = pkg.localPkg()
        if pkg.remote_url.startswith("file://"):
            pkgbasename = "media/%s" % pkg.relativepath
            pkgbasenames.add(pkgbasename)
            continue
        if not os.path.exists(pkgpath):
            log.warning("%s missing", pkgpath)
            continue
        pkgbasename = os.path.basename(pkgpath)
        pkgbasenames.add(pkgbasename)
        target = os.path.join(packagedir, pkgbasename)
        if os.path.exists(target) and os.lstat(pkgpath) == os.lstat(target):
            log.info("%s already in packagedir", pkgbasename)
            continue
        else:
            if os.path.isdir(target):
                log.info("deleting weirdo directory named %s", pkgbasename)
                rm_rf(target)
            elif os.path.exists(target):
                os.remove(target)
            try:
                os.link(pkgpath, target)
            except OSError as e:
                if e.errno == 18:
                    copy2(pkgpath, target)
                else:
                    raise

    # remove spurious / leftover RPMs
    for f in os.listdir(packagedir):
        if f.endswith(".rpm") and f not in pkgbasenames:
            os.remove(os.path.join(packagedir, f))

    # write packagelist
    with open(packagelist, 'w') as outf:
        outf.writelines(p+'\n' for p in pkgbasenames)

    # write cleanup data
    with Config(upgradeconf) as conf:
        # packagedir should probably be last, since it contains upgradeconf
        cleanupdirs = [cachedir, packagedir]
        conf.set("cleanup", "dirs", ';'.join(cleanupdirs))

def setup_upgradelink():
    log.info("setting up upgrade symlink: %s->%s", upgradelink, packagedir)
    try:
        os.remove(upgradelink)
    except OSError:
        pass
    os.symlink(packagedir, upgradelink)

def setup_media_mount(mnt):
    # make a "media" subdir where all the packages are
    mountpath = os.path.join(upgradelink, "media")
    log.info("setting up mount for %s at %s", mnt.dev, mountpath)
    mkdir_p(mountpath)
    # make a directory to place a unit
    mkdir_p(upgrade_prep_dir)
    # make a modified mnt entry that puts it at mountpath
    mediamnt = mnt._replace(rawmnt=mountpath)
    # finally, write out a systemd unit to mount media there
    unit = write_prep_mount(mediamnt, upgrade_prep_dir)
    log.info("wrote %s", unit)

def setup_upgraderoot():
    if os.path.isdir(upgraderoot):
        log.info("upgrade root dir %s already exists", upgraderoot)
        return
    else:
        log.info("creating upgraderoot dir: %s", upgraderoot)
        os.makedirs(upgraderoot, 0755)

def prep_upgrade(pkgs):
    # put packages in packagedir (also writes packagelist)
    link_pkgs(pkgs)
    # make magic symlink
    setup_upgradelink()
    # make dir for upgraderoot
    setup_upgraderoot()

def init_is_systemd():
    try:
        return "systemd" in os.readlink("/sbin/init")
    except OSError:
        return False

def modify_bootloader(kernel, initrd):
    log.info("adding new boot entry")

    args = ["upgrade"]
    remove_args = ["rhgb", "quiet"]
    if init_is_systemd():
        args.append("systemd.unit=system-upgrade.target")
    else:
        args.append("init=/usr/libexec/upgrade-init") # XXX hardcoded path :/

    if not is_selinux_enabled():
        args.append("selinux=0")
    else:
        # BLERG. SELinux enforcing will cause problems if the new policy
        # disallows something that the previous system did differently.
        # See https://bugzilla.redhat.com/bugzilla/show_bug.cgi?id=896010
        args.append("enforcing=0")

    # Workaround for systemd not reaching sysinit.target in RHEL7 dracut
    args.append('rd.plymouth=0')
    args.append('plymouth.enable=0')

    # Leave the network names alone so that the RHEL-6 initscripts can
    # bring interfaces up
    args.append('net.ifnames=0')

    # Screen blanking just makes the screen broken
    args.append("consoleblank=0")

    boot.add_entry(kernel, initrd, banner=_("System Upgrade"), kargs=args,
            remove_kargs=remove_args)

def prep_boot(kernel, initrd):
    # check for systems that need mdadm.conf
    if boot.need_mdadmconf():
        log.info("appending /etc/mdadm.conf to initrd")
        boot.initramfs_append_files(initrd, "/etc/mdadm.conf")

    # look for updates, and add them to initrd if found
    updates = []
    try:
        updates = list(listdir(update_img_dir))
    except (IOError, OSError) as e:
        log.info("can't list update img dir %s: %s", update_img_dir, e.strerror)
    if updates:
        log.info("found updates in %s, appending to initrd", update_img_dir)
        boot.initramfs_append_images(initrd, updates)

    # make a dir in /lib/modules to hold a copy of the new kernel's modules
    # (the initramfs will copy/bind them into place when we reboot)
    kv = kernelver(kernel)
    if kv:
        moddir = os.path.join("/lib/modules", kv)
        log.info("creating module dir %s", moddir)
        mkdir_p(moddir)
    else:
        log.warn("can't determine version of kernel image '%s'", kernel)

    # set up the boot args
    modify_bootloader(kernel, initrd)

def reset_boot():
    '''reset bootloader to previous default and remove our boot entry'''
    conf = Config(upgradeconf)
    kernel = conf.get("boot", "kernel")
    if kernel:
        boot.remove_entry(kernel)

def remove_boot():
    '''remove boot images'''
    conf = Config(upgradeconf)
    kernel = conf.get("boot", "kernel")
    initrd = conf.get("boot", "initrd")
    if kernel:
        rm_f(kernel)
    if initrd:
        rm_f(initrd)

def remove_cache():
    '''remove our cache dirs'''
    conf = Config(upgradeconf)
    cleanup = conf.get("cleanup", "dirs") or ''
    cleanup = cleanup.split(';')
    cleanup += [cachedir, packagedir] # just to be sure
    for d in cleanup:
        log.info("removing %s", d)
        rm_rf(d)

def disable_old_repos():
    repodir = '/etc/yum.repos.d'

    for repo in glob.glob(repodir + '/*.repo'):
        parser = YumRepoParser()
        parser.read(repo)

        repo_changed = False
        for section in parser.sections():
            enabled = '0'
            try:
                enabled = parser.get(section, 'enabled')
            except NoOptionError:
                enabled = '1'

            if enabled == '1':
                parser.set(section, 'enabled', YumRepoParser.DISABLE)
                repo_changed = True

        if repo_changed:
            with open(repo, 'w') as repofile:
                parser.write(repofile)

def misc_cleanup():
    log.info("removing symlink %s", upgradelink)
    rm_f(upgradelink)
    for d in (upgraderoot, upgrade_prep_dir):
        log.info("removing %s", d)
        rm_rf(d)

    repodir = '/etc/yum.repos.d'

    log.info("removing repo files")
    for repo in glob.glob(repodir + '/redhat-upgrade-*.repo'):
        rm_rf(repo)

    # Un-disable the repo files
    for repo in glob.glob(repodir + '/*.repo'):
        with open(repo, 'r') as repofile:
            repodata = repofile.read()
        enabled_data = re.sub('# disabled by redhat-upgrade-tool\nenabled\\s*=\\s*0', 'enabled=1', repodata)
        if enabled_data != repodata:
            with open(repo, 'w') as repofile:
                repofile.write(enabled_data)

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
