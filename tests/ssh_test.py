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

from libup import ssh


@pytest.mark.parametrize('output,expected', [
    ('256 SHA256:<hash> tools.libraryupgrader@tools.wmflabs.org (ED25519)',
     True),
    ('The agent has no identities.', False)
])
def test_is_key_loaded(mocker, output, expected):
    check_call = mocker.patch('libup.ssh.ShellMixin.check_call')
    check_call.return_value = output
    is_agent_running = mocker.patch('libup.ssh.is_agent_running')
    is_agent_running.return_value = True
    assert ssh.is_key_loaded() is expected
