#!/usr/bin/python
#
# redhat-upgrade-tool.py - commandline frontend for redhat-upgrade-tool, the
# Red Hat Upgrade Tool.
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

import os, sys, time, platform, shutil
from subprocess import call, check_call, CalledProcessError, Popen, PIPE
from ConfigParser import NoOptionError

from redhat_upgrade_tool.util import rm_f, mkdir_p
from redhat_upgrade_tool.download import UpgradeDownloader, YumBaseError, yum_plugin_for_exc, URLGrabError
from redhat_upgrade_tool.sysprep import prep_upgrade, prep_boot, setup_media_mount, setup_cleanup_post
from redhat_upgrade_tool.upgrade import RPMUpgrade, TransactionError

from redhat_upgrade_tool.commandline import parse_args, do_cleanup, device_setup
from redhat_upgrade_tool import textoutput as output
from redhat_upgrade_tool import upgradeconf

import redhat_upgrade_tool.logutils as logutils
import redhat_upgrade_tool.media as media

try:
    from preup import xccdf
    from preup import settings
    preupgrade_available = True
except ImportError:
    preupgrade_available = False


import logging
log = logging.getLogger("redhat-upgrade-tool")
def message(m):
    print m
    log.info(m)

from redhat_upgrade_tool import _, kernelpath, initrdpath

def setup_downloader(version, instrepo=None, cacheonly=False, repos=[],
                     enable_plugins=[], disable_plugins=[]):
    log.debug("setup_downloader(version=%s, repos=%s)", version, repos)
    f = UpgradeDownloader(version=version, cacheonly=cacheonly)
    f.preconf.enabled_plugins += enable_plugins
    f.preconf.disabled_plugins += disable_plugins
    f.instrepoid = instrepo
    repo_cb = output.RepoCallback()
    repo_prog = output.RepoProgress(fo=sys.stderr)
    disabled_repos = f.setup_repos(callback=repo_cb,
                                   progressbar=repo_prog,
                                   repos=repos)
    disabled_repos = filter(lambda id: id != f.instrepoid, disabled_repos)
    if disabled_repos:
        print _("No upgrade available for the following repos") + ": " + \
                " ".join(disabled_repos)
        print _("Check that the repo URLs are correct.")
        log.info("disabled repos: " + " ".join(disabled_repos))
    return f

def download_packages(f):
    updates = f.build_update_transaction(callback=output.DepsolveCallback(f))
    # check for empty upgrade transaction
    if not updates:
        print _('Your system is already upgraded!')
        print _('Finished. Nothing to do.')
        raise SystemExit(0)
    # print dependency problems before we start the upgrade
    transprobs = f.describe_transaction_problems()
    if transprobs and not major_upgrade:
        print "WARNING: potential problems with upgrade"
        for p in transprobs:
            print "  " + p
    # clean out any unneeded packages from the cache
    f.clean_cache(keepfiles=(p.localPkg() for p in updates))
    # download packages
    f.download_packages(updates, callback=output.DownloadCallback())

    return updates

def transaction_test(pkgs):
    print _("testing upgrade transaction")
    pkgfiles = set(po.localPkg() for po in pkgs)
    fu = RPMUpgrade()
    probs = fu.setup_transaction(pkgfiles=pkgfiles, check_fatal=False)
    rv = fu.test_transaction(callback=output.TransactionCallback(numpkgs=len(pkgfiles)))
    return (probs, rv)

def reboot():
    call(['systemctl', 'reboot'])

def get_preupgrade_result_name():
    if preupgrade_available:
        return os.path.join(settings.result_dir, settings.xml_result_name)
    else:
        return None

def main(args):
    global major_upgrade

    if args.clean:
        do_cleanup(args)
        return

    if args.device or args.iso:
        device_setup(args)

    # Get our packages set up where we can use 'em
    print _("setting up repos...")
    f = setup_downloader(version=args.network,
                         cacheonly=args.cacheonly,
                         instrepo=args.instrepo,
                         repos=args.repos,
                         enable_plugins=args.enable_plugins,
                         disable_plugins=args.disable_plugins)

    # Compare the first part of the version number in the treeinfo with the
    # first part of the version number of the system to determine if this is a
    # major version upgrade
    if f.treeinfo.get('general', 'version').split('.')[0] != \
            platform.linux_distribution()[1].split('.')[0]:

        major_upgrade = True

        # Check if preupgrade-assistant has been run
        if args.force:
            log.info("Skipping check for preupgrade-assisant")

        if not args.force and preupgrade_available:
            # Run preupg --riskcheck
            returncode = xccdf.check_inplace_risk(get_preupgrade_result_name(), 0)
            if int(returncode) == 0:
                print _("Preupgrade assistant does not found any risks")
                print _("Upgrade will continue.")
            elif int(returncode) == 1:
                print _("Preupgrade assistant risk check found risks for this upgrade.")
                print _("You can run preupg --riskcheck --verbose to view these risks.")
                print _("Addressing high risk issues is required before the in-place upgrade")
                print _("and ignoring these risks may result in a broken upgrade and unsupported upgrade.")
                print _("Please backup your data.")
                print ""
                print _("List of issues:")

                xccdf.check_inplace_risk(get_preupgrade_result_name(), verbose=2)

                answer = raw_input(_("Continue with the upgrade [Y/N]? "))
                # TRANSLATORS: y for yes
                if answer.lower() != _('y'):
                    raise SystemExit(1)
            elif int(returncode) == 2:
                print _("preupgrade-assistant risk check found EXTREME risks for this upgrade.")
                print _("Run preupg --riskcheck --verbose to view these risks.")
                print _("Continuing with this upgrade is not recommended.")
                raise SystemExit(1)
            else:
                print _("preupgrade-assistant has not been run.")
                print _("To perform this upgrade, either run preupg or run redhat-upgrade-tool --force")
                raise SystemExit(1)

    # Check that we are upgrading to the same variant
    if not args.force:
        distro = platform.linux_distribution()[0]
        if not distro.startswith("Red Hat Enterprise Linux "):
            print _("Invalid distribution: %s") % distro
            raise SystemExit(1)

        from_variant = distro[len('Red Hat Enterprise Linux '):]
        try:
            to_variant = f.treeinfo.get('general', 'variant')
        except NoOptionError:
            print _("Upgrade repository is not a Red Hat Enterprise Linux repository")
            raise SystemExit(1)

        if from_variant != to_variant:
            print _("Upgrade requested from Red Hat Enterprise Linux %s to %s") % (from_variant, to_variant)
            print _("Upgrades between Red Hat Enterprise Linux variants is not supported.")
            raise SystemExit(1)
    else:
        log.info("Skipping variant check")

    if args.nogpgcheck:
        f._override_sigchecks = True

    if args.expire_cache:
        print "expiring cache files"
        f.cleanExpireCache()
        return
    if args.clean_metadata:
        print "cleaning metadata"
        f.cleanMetadata()
        return

    # Cleanup old conf files
    log.info("Clearing %s", upgradeconf)
    rm_f(upgradeconf)
    mkdir_p(os.path.dirname(upgradeconf))

    # TODO: error msg generation should be shared between CLI and GUI
    if args.skipkernel:
        message("skipping kernel/initrd download")
    elif f.instrepoid is None or f.instrepoid in f.disabled_repos:
        print _("Error: can't get boot images.")
        if args.instrepo:
            print _("The '%s' repo was rejected by yum as invalid.") % args.instrepo
            if args.iso:
                print _("The given ISO probably isn't an install DVD image.")
                media.umount(args.device.mnt)
            elif args.device:
                print _("The media doesn't contain a valid install DVD image.")
        else:
            print _("The installation repo isn't currently available.")
            print _("Try again later, or specify a repo using --instrepo.")
        raise SystemExit(1)
    else:
        print _("getting boot images...")
        kernel, initrd = f.download_boot_images() # TODO: force arch?

    if args.skippkgs:
        message("skipping package download")
    else:
        print _("setting up update...")
        if len(f.pkgSack) == 0:
            print("no updates available in configured repos!")
            raise SystemExit(1)
        pkgs = download_packages(f)
        # Run a test transaction
        probs, rv = transaction_test(pkgs)


    # And prepare for upgrade
    # TODO: use polkit to get root privs for these things
    print _("setting up system for upgrade")
    if not args.skippkgs:
        prep_upgrade(pkgs)

    # Save the repo configuration
    f.save_repo_configs()

    if not args.skipbootloader:
        if args.skipkernel:
            print "warning: --skipkernel without --skipbootloader"
            print "using default paths: %s %s" % (kernelpath, initrdpath)
            kernel = kernelpath
            initrd = initrdpath
        prep_boot(kernel, initrd)

    if args.device:
        setup_media_mount(args.device)

    if args.iso:
        media.umount(args.device.mnt)

    if args.cleanup_post:
        setup_cleanup_post()

    # Workaround the redhat-upgrade-dracut upgrade-post hook order problem
    # Copy upgrade.conf to /root/preupgrade so that it won't be removed
    # before the postupgrade scripts are run.
    mkdir_p('/root/preupgrade')
    shutil.copyfile(upgradeconf, '/root/preupgrade/upgrade.conf')

    if args.reboot:
        reboot()
    else:
        print _('Finished. Reboot to start upgrade.')

    # --- Here's where we summarize potential problems. ---

    # list packages without updates, if any
    missing = sorted(f.find_packages_without_updates(), key=lambda p:p.envra)
    if missing and not major_upgrade:
        message(_('Packages without updates:'))
        for p in missing:
            message("  %s" % p)

    # warn if the "important" repos are disabled
    #if f.disabled_repos:
        # NOTE: I hate having a hardcoded list of Important Repos here.
        # This information should be provided by the system, somehow..
        #important = ("fedora", "updates")
        #if any(i in f.disabled_repos for i in important):
        #    msg = _("WARNING: Some important repos could not be contacted: %s")
        #else:
        #    msg = _("NOTE: Some repos could not be contacted: %s")
        #print msg % ", ".join(f.disabled_repos)
        #print _("If you start the upgrade now, packages from these repos will not be installed.")

    # warn about broken dependencies etc.
    # If this is a major version upgrade, the user has already been warned
    # about all of this from preupgrade-assistant, so skip the warning here
    if probs and not major_upgrade:
        print
        print _("WARNING: problems were encountered during transaction test:")
        for s in probs.summaries:
            print "  "+s.desc
            for line in s.format_details():
                print "    "+line
        print _("Continue with the upgrade at your own risk.")

if __name__ == '__main__':
    args = parse_args()
    major_upgrade = False

    # TODO: use polkit to get privs for modifying bootloader stuff instead
    if os.getuid() != 0:
        print _("you must be root to run this program.")
        raise SystemExit(1)

    # set up logging
    if args.debuglog:
        logutils.debuglog(args.debuglog)
    logutils.consolelog(level=args.loglevel)
    log.info("%s starting at %s", sys.argv[0], time.asctime())

    try:
        exittype = "cleanly"
        main(args)
    except KeyboardInterrupt as e:
        print
        log.info("exiting on keyboard interrupt")
        if e.message:
            message(_("Exiting on keyboard interrupt (%s)") % e.message)
        raise SystemExit(1)
    except (YumBaseError, URLGrabError) as e:
        print
        if hasattr(e, "value") and isinstance(e.value, list):
            err = e.value.pop(0)
            message(_("Downloading failed: %s") % err)
            for p in e.value:
                message("  %s" % p)
        else:
            message(_("Downloading failed: %s") % e)
        log.debug("Traceback (for debugging purposes):", exc_info=True)
        raise SystemExit(2)
    except TransactionError as e:
        print
        message(_("Upgrade test failed with the following problems:"))
        for s in e.summaries:
            message(s)
        log.debug("Detailed transaction problems:")
        for p in e.problems:
            log.debug(p)
        log.error(_("Upgrade test failed."))
        raise SystemExit(3)
    except Exception as e:
        pluginfile = yum_plugin_for_exc()
        if pluginfile:
            plugin, ext = os.path.splitext(os.path.basename(pluginfile))
            log.error(_("The '%s' yum plugin has crashed.") % plugin)
            log.error(_("Please report this problem to the plugin developers:"),
                      exc_info=True)
            raise SystemExit(1)
        log.info("Exception:", exc_info=True)
        exittype = "with unhandled exception"
        raise
    finally:
        log.info("%s exiting %s at %s", sys.argv[0], exittype, time.asctime())
