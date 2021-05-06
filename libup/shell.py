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
import subprocess

from . import GIT_EMAIL, GIT_NAME, utils


class ShellMixin:
    def check_call(self, args: list, stdin='', env=None,
                   ignore_returncode=False) -> str:
        debug = self.log if hasattr(self, 'log') else print  # type: ignore
        debug('$ ' + ' '.join(args))
        res = subprocess.run(
            args,
            input=stdin.encode(),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=env,
        )
        debug(res.stdout.decode())
        if not ignore_returncode:
            res.check_returncode()
        return res.stdout.decode()

    def git_sha1(self, branch: str) -> str:
        return self.check_call(['git', 'show-ref', f'refs/heads/{branch}']).split(' ')[0]

    def clone(self, repo, branch='master', internal=False):
        url = utils.gerrit_url(repo, internal=internal)
        self.check_call(['git', 'clone', url, 'repo', '--depth=1', '-b', branch])
        os.chdir('repo')
        self.check_call(['git', 'config', 'user.name', GIT_NAME])
        self.check_call(['git', 'config', 'user.email', GIT_EMAIL])
        self.check_call(['git', 'submodule', 'update', '--init'])
