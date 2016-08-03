# repofile.py - alters .repo files (adds or replaces repo options)
#
# Copyright (C) 2016 Red Hat Inc.
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

import re


class RepoFileParser(object):
    def __init__(self, repo_file):
        self._repo_file = repo_file
        self._repo_file_content = self._get_repo_file_content()
        self._repo_ids = self._get_repo_ids()

    def _get_repo_file_content(self):
        with open(self._repo_file) as file_to_read:
            return file_to_read.read()

    def _get_repo_ids(self):
        """Retrieve IDs of all the repositories within the .repo file."""
        return re.findall("^\s*\[(.*?)\]\s*$",
                          self._repo_file_content,
                          re.MULTILINE)

    def set_option(self, option_name, value_to_set, orig_value=None):
        """Go through all the the repo IDs (sections) within the repo file
        and set new value of a specific repository option. The option is
        added if it does not exist. Optional parameter orig_value causes that
        the repository option value is replaced only if the current value
        matches the orig_value.
        """
        for repo_id in self._repo_ids:
            # Search for the option among repo ID options
            current_value = self._get_option_value(repo_id, option_name)
            if current_value:
                if orig_value and current_value != orig_value:
                    continue
                self._replace_option_value(repo_id, option_name, value_to_set)
            elif not current_value:
                # The option isn't present - add it
                self._add_option(repo_id, option_name, value_to_set)

    def _get_option_value(self, repo_id, option_name):
        """Return value of an option present under a specific repo ID.
        Return None if the option is not found.
        """
        option_found = re.search(
            r"\[{0}\][^\[]*?{1}\s*=\s*(\S+)\s*$"
            .format(repo_id, option_name),
            self._repo_file_content, flags=re.MULTILINE | re.DOTALL)
        return option_found.group(1) if option_found else None

    def _replace_option_value(self, repo_id, option_name, option_value):
        pattern = re.compile(
            r"(\[{0}\][^\[]*?{1}\s*=\s*).*?$".format(repo_id, option_name),
            flags=re.MULTILINE)
        self._repo_file_content = pattern.sub(
            r"\g<1>{0}".format(option_value), self._repo_file_content)

    def _add_option(self, repo_id, option_name, option_value):
        """Add a new option after the baseurl option within the section of
        a specific repo ID.
        """
        pattern = re.compile(r"(\[{0}\].*?baseurl.*?)$".format(repo_id),
                             flags=re.MULTILINE | re.DOTALL)
        self._repo_file_content = pattern.sub(
            r"\1\n{0}={1}".format(option_name, option_value),
            self._repo_file_content)

    def write(self):
        """Write the altered repo file content to the original file."""
        with open(self._repo_file, 'w') as file_to_write:
            file_to_write.write(self._repo_file_content)
