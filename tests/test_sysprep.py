from collections import namedtuple
from mock import MagicMock
from redhat_upgrade_tool import sysprep


def test_setup_upgradelink():
    """ setup_upgradelink will set up the symlink between packagedir and upgradelink """
    sysprep.os.symlink = MagicMock(return_value=True)
    sysprep.setup_upgradelink()
    sysprep.os.symlink.assert_called_once_with('/var/lib/system-upgrade', '/system-upgrade')


def test_setup_media_mount():
    """ setup_media_mount will set up a mount for mnt.dev """
    sysprep.mkdir_p = MagicMock(return_value=True)
    sysprep.write_systemd_unit = MagicMock(return_value=True)
    Device = namedtuple('Device', ['dev', 'rawmnt'])
    mnt = Device(dev='dev', rawmnt='rawmnt')
    sysprep.setup_media_mount(mnt)
    sysprep.write_systemd_unit.assert_called_once_with(Device(dev='dev', rawmnt='/system-upgrade/media'),
                                                       '/lib/systemd/system/system-upgrade.target.requires')


def test_setup_upgraderoot():
    """ setup_upgraderoot will set up upgraderoot path """
    sysprep.os.path.isdir = MagicMock(return_value=False)
    sysprep.os.makedirs = MagicMock(return_value=True)
    sysprep.setup_upgraderoot()
    sysprep.os.makedirs.assert_called_once_with('/system-upgrade-root', 0755)
