#!/usr/bin/python

import json
import os
import re
import shlex
import subprocess
import ConfigParser

Config = ConfigParser.ConfigParser()
Config.read("/boot/grub/snapshot.metadata")


def run_subprocess(cmd, print_output=True):
    """
    Call the passed command and optionally print its output.
    """
    cmd = shlex.split(cmd, False)
    sp_popen = subprocess.Popen(cmd,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT,
                                bufsize=1)
    stdout = ''
    for line in iter(sp_popen.stdout.readline, ''):
        stdout += line
    sp_popen.communicate()

    return stdout, sp_popen.returncode


def load_json(input_file):
    with open(input_file, 'r') as f:
        return json.load(f)


def get_config_sections(section):
    dict1 = {}
    options = Config.options(section)
    for option in options:
        try:
            dict1[option] = Config.get(section, option)
        except:
            dict1[option] = None
    return dict1


def get_snapshot_path():
    snapshot_paths = []
    for part in Config.sections():
        name = get_config_sections(part)['name']
        origin_lv = get_config_sections(part)['origin_lv']
        vg_name, lv_name = origin_lv.split('/')
        lv_name = name
        snapshot_path = os.path.join('/dev', vg_name, lv_name)
        snapshot_paths.append(snapshot_path)
    return snapshot_paths


def remove_snapshot():
    for snapshot in get_snapshot_path():
        if os.path.exists(snapshot):
            print "Removing {} snapshot".format(snapshot)
            subprocess.call(['lvremove', '-f', snapshot])


def remove_snap_boot_files():
    snap_boot_files_data = load_json('/boot/manualcleanup/snap_boot_files')
    for snap_boot_file in snap_boot_files_data:
        if os.path.isfile(snap_boot_file):
            print snap_boot_file, " will be deleted"
            os.remove(snap_boot_file)


def remove_loader_cache():
    directory = '/boot/loader/entries'
    for filename in os.listdir(directory):
        filename = os.path.join(directory, filename)
        if os.path.isfile(filename):
            print "Deleting ", filename
            os.remove(filename)


def clean_grub_entry():
    return run_subprocess('grubby --grub --remove-kernel=/boot/vmlinuz-snapshot')


remove_snap_boot_files()
remove_snapshot()
remove_loader_cache()
clean_grub_entry()
