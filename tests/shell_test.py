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

from libup.shell import ShellMixin


def test_check_call():
    shell = ShellMixin()
    # output
    assert 'hi\n' == shell.check_call(['echo', 'hi'])
    # errors
    with pytest.raises(subprocess.CalledProcessError):
        shell.check_call(['false'])
    # stdin
    assert 'test' == shell.check_call(['tee'], stdin='test')
    # env
    assert 'TEST=foo\n' == shell.check_call(['env'], env={'TEST': 'foo'})
