"""
Copyright (C) 2019 Kunal Mehta <legoktm@member.fsf.org>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import pytest
import subprocess

from ng import LibraryUpgrader


class MockLibraryUpgrader(LibraryUpgrader):
    def __init__(self):
        self.called = []

    def check_call(self, args: list) -> str:
        self.called.append(args)
        return ' '.join(args)


def test_gerrit_url():
    libup = LibraryUpgrader()
    assert libup.gerrit_url('repo/name') \
        == 'https://gerrit.wikimedia.org/r/repo/name.git'
    assert libup.gerrit_url('repo/name', user='foo') \
        == 'https://foo@gerrit.wikimedia.org/r/repo/name.git'
    assert libup.gerrit_url('repo/name', user='foo', pw='bar!!+/') \
        == 'https://foo:bar%21%21%2B%2F@gerrit.wikimedia.org/r/repo/name.git'


def test_has_npm(fs):
    libup = LibraryUpgrader()
    assert libup.has_npm is False
    fs.create_file('package.json', contents='{}')
    assert libup.has_npm is True


def test_has_composer(fs):
    libup = LibraryUpgrader()
    assert libup.has_composer is False
    fs.create_file('composer.json', contents='{}')
    assert libup.has_composer is True


def test_check_call():
    libup = LibraryUpgrader()
    res = libup.check_call(['echo', 'hi'])
    assert res == 'hi\n'


def test_check_call_fail():
    libup = LibraryUpgrader()
    with pytest.raises(subprocess.CalledProcessError):
        libup.check_call(['false'])


def test_ensure_package_lock(fs):
    libup = MockLibraryUpgrader()
    libup.ensure_package_lock()
    assert libup.called == [['npm', 'i', '--package-lock-only']]
    libup = MockLibraryUpgrader()
    fs.create_file('package-lock.json', contents='{}')
    libup.ensure_package_lock()
    assert libup.called == []
