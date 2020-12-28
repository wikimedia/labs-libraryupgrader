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
    pusher = Pusher('master')
    check_call = mocker.patch('libup.push.Pusher.check_call')
    check_call.return_value = GIT_OUTPUT
    assert {
        'README => README.md',
        'includes/Hooks.php',
        'sample.php => something.php'
    } == pusher.changed_files()


def test_build_push_command():
    pusher = Pusher('REL1_35')
    options = {
        "repo": "test/example",
        "hashtags": ["CVE-2000-1234"],
        "message": "View logs",
        "vote": "Code-Review+2",
    }
    assert [
        'git', 'push',
        'ssh://libraryupgrader@gerrit.wikimedia.org:29418/test/example',
        'HEAD:refs/for/REL1_35%topic=bump-dev-deps,t=CVE-2000-1234,l=Code-Review+2,m=View+logs'
    ] == pusher.build_push_command(options)
    options['vote'] = ''
    assert [
        'git', 'push',
        'ssh://libraryupgrader@gerrit.wikimedia.org:29418/test/example',
        'HEAD:refs/for/REL1_35%topic=bump-dev-deps,t=CVE-2000-1234,m=View+logs'
    ] == pusher.build_push_command(options)
