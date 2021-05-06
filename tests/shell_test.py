"""
Copyright (C) 2019 Kunal Mehta <legoktm@debian.org>

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

import os
import pytest
import subprocess

from libup.shell import ShellMixin

HELPER = os.path.join(os.path.dirname(__file__), 'shell_helper.py')


def test_check_call():
    shell = ShellMixin()
    # output
    assert 'hi\n' == shell.check_call(['echo', 'hi'])
    # errors
    with pytest.raises(subprocess.CalledProcessError):
        shell.check_call(['false'])
    # no exception raised
    assert '' == shell.check_call(['false'], ignore_returncode=True)
    # stdin
    assert 'test' == shell.check_call(['tee'], stdin='test')
    # env
    assert 'TEST=foo\n' == shell.check_call(['env'], env={'TEST': 'foo'})


def test_integration():
    output = []
    shell = ShellMixin()
    shell.log = output.append
    expected = 'this goes to stderr\nthis goes to stdout\n'
    assert expected == shell.check_call(['python3', HELPER])
    assert expected in output


def test_integration_fail():
    output = []
    shell = ShellMixin()
    shell.log = output.append
    expected = 'this goes to stderr\nthis goes to stdout\n'
    with pytest.raises(subprocess.CalledProcessError):
        shell.check_call(['python3', HELPER, '--fail'])
    assert expected in output


def test_git_sha1(mocker):
    shell = ShellMixin()
    check_call = mocker.patch.object(shell, 'check_call')
    check_call.return_value = \
        '44560cc7288485f23988bf2e35cc20518f37b2ee refs/remotes/origin/HEAD'
    assert '44560cc7288485f23988bf2e35cc20518f37b2ee' == shell.git_sha1(branch="master")
