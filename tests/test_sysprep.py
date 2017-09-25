from collections import namedtuple
from mock import MagicMock
from redhat_upgrade_tool import sysprep


def test_setup_upgradelink():
    """ setup_upgradelink will set up the symlink between packagedir and upgradelink """
    sysprep.os.symlink = MagicMock(return_value=True)
    sysprep.setup_upgradelink()
    sysprep.os.symlink.assert_called_once_with('/var/lib/system-upgrade', '/system-upgrade')


def test_setup_upgraderoot():
    """ setup_upgraderoot will set up upgraderoot path """
    sysprep.os.path.isdir = MagicMock(return_value=False)
    sysprep.os.makedirs = MagicMock(return_value=True)
    sysprep.setup_upgraderoot()
    sysprep.os.makedirs.assert_called_once_with('/system-upgrade-root', 0755)
