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

import subprocess
import urllib.parse

from . import GERRIT_USER, SSH_AUTH_SOCK, config, gerrit, shell, utils

AUTO_APPROVE_FILES = {
    'composer.json',
    'package.json',
    'package-lock.json',
    'phpcs.xml',
    '.phpcs.xml',
    'phpcs.xml => .phpcs.xml',
    '.eslintrc',
    '.eslintrc.json',
    '.eslintrc => .eslintrc.json',
    '.stylelintrc => .stylelintrc.json',
    'CODE_OF_CONDUCT.md',
    '.gitignore',
    'Gruntfile.js',
}


class Pusher(shell.ShellMixin):
    def __init__(self, branch):
        self.branch = branch

    def changed_files(self):
        out = self.check_call(['git', 'log', '--stat', '--oneline', '-n1'])
        lines = out.splitlines()
        # Drop the first and last lines
        lines.pop(0)
        lines.pop()
        changed = set()
        for line in lines:
            changed.add(line.rsplit('|', 1)[0].strip())

        return changed

    def can_autoapprove(self):
        return self.changed_files().issubset(AUTO_APPROVE_FILES)

    def build_push_command(self, options: dict) -> list:
        per = '%topic=bump-dev-deps'
        for hashtag in options['hashtags']:
            per += ',t=' + hashtag
        if options.get('vote'):
            per += ',l=' + options['vote']
            # If we're not automerging, vote V+1 to trigger jenkins (T254070)
        if options.get('message'):
            per += ',m=' + urllib.parse.quote_plus(options['message'])
        return ['git', 'push',
                utils.gerrit_url(options['repo'], GERRIT_USER, ssh=True),
                f'HEAD:refs/for/{self.branch}' + per]

    def git_push(self, repo: str, hashtags: list, message='', plus2=False, push=False):
        options = {
            'repo': repo,
            'hashtags': hashtags,
            'message': message,
        }
        if plus2:
            options['vote'] = 'Code-Review+2'
        else:
            # If we're not automerging, vote V+1 to trigger jenkins (T254070)
            options['vote'] = 'Verified+1'
        env = {'SSH_AUTH_SOCK': SSH_AUTH_SOCK}
        if push:
            try:
                self.check_call(self.build_push_command(options), env=env)
            except subprocess.CalledProcessError:
                if options['vote'] == 'Code-Review+2':
                    # Try again without CR+2
                    options['vote'] = 'Verified+1'
                    try:
                        self.check_call(self.build_push_command(options), env=env)
                    except subprocess.CalledProcessError:
                        # And try again again without V+1
                        options['vote'] = ''
                        self.check_call(self.build_push_command(options), env=env)
                else:
                    # Try again without V+1
                    options['vote'] = ''
                    self.check_call(self.build_push_command(options), env=env)
        else:
            print('SIMULATE: '.join(self.build_push_command(options)))

    def run(self, info):
        if not info.get('patch'):
            print('No patch...?')
            return
        self.clone(info['repo'], branch=self.branch, internal=True)
        # TODO: investigate doing some diff/sanity check to make sure
        # the deps match updates
        self.check_call(['git', 'am'], stdin=info['patch'])
        hashtags = info.get('hashtags', [])
        message = info.get('message', '')
        plus2 = self.can_autoapprove()
        # Flood control, don't overload zuul...
        gerrit.wait_for_zuul_test_gate(count=3)
        push = config.should_push()
        self.git_push(info['repo'], hashtags=hashtags, message=message,
                      plus2=plus2, push=push)
