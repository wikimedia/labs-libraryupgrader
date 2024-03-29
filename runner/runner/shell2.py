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


GIT_NAME = 'libraryupgrader'
GIT_EMAIL = 'tools.libraryupgrader@tools.wmflabs.org'


class ShellMixin:
    def check_call(self, args: list, stdin='', env=None,
                   ignore_returncode=False) -> str:
        # Avoid CVE-2020-5252 style attacks by ensuring that `npm ...` or
        # `composer ...` cannot be hijacked by forcing use of explicit binaries
        # owned by root.
        if args[0] == 'npm':
            args[0] = '/usr/bin/npm'
        elif args[0] == 'composer':
            args[0] = '/usr/bin/composer'
        debug = self.log if hasattr(self, 'log') else print  # type: ignore
        debug('$ ' + ' '.join(args))
        res = subprocess.run(
            args,
            input=stdin.encode(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )
        stderr = res.stderr.decode().strip()
        if stderr:
            debug('--- stderr ---')
            debug(stderr)
        debug('--- stdout ---')
        stdout = res.stdout.decode()
        debug(stdout)
        debug('--- end ---')
        if not ignore_returncode:
            res.check_returncode()
        return stdout

    def git_sha1(self, branch: str) -> str:
        return self.check_call(['git', 'show-ref', f'refs/heads/{branch}']).split(' ')[0]

    def clone(self, repo, branch='master', internal=False):
        url = gerrit_url(repo, internal=internal)
        self.check_call(['git', 'clone', url, 'repo', '--depth=1', '-b', branch])
        os.chdir('repo')
        self.check_call(['git', 'config', 'user.name', GIT_NAME])
        self.check_call(['git', 'config', 'user.email', GIT_EMAIL])
        self.check_call(['git', 'submodule', 'update', '--init'])


def gerrit_url(repo: str, internal=False) -> str:
    if internal:
        return f'file:///srv/git/{repo.replace("/", "-")}.git'
    else:
        return f'https://gerrit-replica.wikimedia.org/r/{repo}.git'
