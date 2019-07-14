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

import os
import subprocess

from . import utils


class ShellMixin:
    def check_call(self, args: list, stdin='', env=None) -> str:
        print('$ ' + ' '.join(args))
        res = subprocess.run(
            args,
            input=stdin.encode(),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=env,
        )
        # TODO: log
        print(res.stdout.decode())
        res.check_returncode()
        return res.stdout.decode()

    def clone(self, repo):
        url = utils.gerrit_url(repo)
        self.check_call(['git', 'clone', url, 'repo', '--depth=1'])
        os.chdir('repo')
        self.check_call(['git', 'submodule', 'update', '--init'])
        self.check_call(['grr', 'init'])  # Install commit-msg hook
