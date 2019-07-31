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

from libup.push import Pusher


GIT_OUTPUT = """37a71cdcc1 This is a test
 README => README.md         | 0
 includes/Hooks.php          | 2 +-
 sample.php => something.php | 2 +-
 3 files changed, 2 insertions(+), 2 deletions(-)
"""


def test_changed_files(mocker):
    pusher = Pusher()
    call_git = mocker.patch('libup.push.Pusher.call_git')
    call_git.return_value = GIT_OUTPUT
    assert {
        'README => README.md',
        'includes/Hooks.php',
        'sample.php => something.php'
    } == pusher.changed_files()
