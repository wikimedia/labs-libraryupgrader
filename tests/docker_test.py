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

from libup import CACHE, docker


def test_run(mocker):
    check_call = mocker.patch('subprocess.check_call')
    docker.run(
        'foobar',
        env={'env1': 'val1'},
        mounts={'/tmp/test': '/test:ro'},
        rm=True,
        entrypoint='/bin/bash',
        extra_args=['libup-ng'],
    )
    check_call.assert_called_once_with([
        'docker', 'run', '--name=foobar', '--env', 'env1=val1',
        '--rm', '--entrypoint', '/bin/bash', '-v', '%s:/cache' % CACHE,
        '-v', '/tmp/test:/test:ro', '-d', 'libraryupgrader', 'libup-ng',
    ])
