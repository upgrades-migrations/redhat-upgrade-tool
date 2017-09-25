import os
from mock import MagicMock
from redhat_upgrade_tool import util


def test_listdir():
    """ listdir returns a list of directory content """
    util.os.listdir = MagicMock(return_value=['file1.txt', 'file2.txt', 'file3.txt'])
    actual = []
    for entry in util.listdir('mockdir'):
        actual.append(entry)
    assert actual == ['mockdir/file1.txt', 'mockdir/file2.txt', 'mockdir/file3.txt']


def test_mkdir_p():
    """ mkdir_p create directories """
    util.os.makedirs = MagicMock(return_value=True)
    util.mkdir_p('/some/mock/path')
    util.os.makedirs.assert_called_once_with('/some/mock/path')


def test_rm_f():
    """ rm_f deletes some file """
    util.os.path.lexists = MagicMock(return_value=True)
    util.os.remove = MagicMock(return_value=True)
    util.rm_f('/some/mock/path', util.os.remove)
    util.os.path.lexists.assert_called_once_with('/some/mock/path')
    util.os.remove.assert_called_once_with('/some/mock/path')


def test_kernelver():
    """ kernelver returns a version from a vmlinuz file """
    basedir = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(basedir, 'data')

    kernel_file = os.path.join(data_path, 'vmlinuz-4.12.9-300.fc26.x86_64')
    assert util.kernelver(kernel_file) == '4.12.9-300.fc26.x86_64'


def test_hrsize():
    """ hrsize converts size to a human readable format """

    data = [
        {'size': 0, 'si': False, 'use_ib': False, 'expected': '1K'},
        {'size': 0, 'si': False, 'use_ib': True, 'expected': '1KiB'},
        {'size': 0, 'si': True, 'use_ib': False, 'expected': '1KB'},
        {'size': 0, 'si': True, 'use_ib': True, 'expected': '1KB'},

        {'size': 42, 'si': False, 'use_ib': False, 'expected': '1K'},
        {'size': 42, 'si': False, 'use_ib': True, 'expected': '1KiB'},
        {'size': 42, 'si': True, 'use_ib': False, 'expected': '1KB'},
        {'size': 42, 'si': True, 'use_ib': True, 'expected': '1KB'},

        {'size': 512, 'si': False, 'use_ib': False, 'expected': '1K'},
        {'size': 512, 'si': False, 'use_ib': True, 'expected': '1KiB'},
        {'size': 512, 'si': True, 'use_ib': False, 'expected': '1KB'},
        {'size': 512, 'si': True, 'use_ib': True, 'expected': '1KB'},

        {'size': 1024, 'si': False, 'use_ib': False, 'expected': '2K'},
        {'size': 1024, 'si': False, 'use_ib': True, 'expected': '2KiB'},
        {'size': 1024, 'si': True, 'use_ib': False, 'expected': '2KB'},
        {'size': 1024, 'si': True, 'use_ib': True, 'expected': '2KB'},

        {'size': 1024 * 1024, 'si': False, 'use_ib': False, 'expected': '2M'},
        {'size': 1024 * 1024, 'si': False, 'use_ib': True, 'expected': '2MiB'},
        {'size': 1024 * 1024, 'si': True, 'use_ib': False, 'expected': '2MB'},
        {'size': 1024 * 1024, 'si': True, 'use_ib': True, 'expected': '2MB'},
    ]

    for entry in data:
        actual = util.hrsize(entry['size'], entry['si'], entry['use_ib'])
        assert actual == entry['expected']
