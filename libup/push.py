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

import argparse
import json
import subprocess

from . import GERRIT_USER, gerrit, shell, utils
from .update import Update

AUTO_APPROVE_FILES = {
    'composer.json',
    'package.json',
    'package-lock.json',
    'phpcs.xml',
    '.phpcs.xml',
    'phpcs.xml => .phpcs.xml',
    'CODE_OF_CONDUCT.md',
}


class Pusher(shell.ShellMixin):
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

    def git_push(self, repo: str, hashtags: list, plus2=False, push=False):
        # TODO: add ssh remote
        self.check_call([
            'git', 'remote', 'add', 'ssh',
            utils.gerrit_url(repo, GERRIT_USER, ssh=True)
        ])
        per = '%topic=bump-dev-deps'
        for hashtag in hashtags:
            per += ',t=' + hashtag
        if plus2:
            per += ',l=Code-Review+2'
        push_cmd = ['git', 'push', 'ssh',
                    'HEAD:refs/for/master' + per]
        env = {'SSH_AUTH_SOCK': '/ssh-agent'}
        if push:
            try:
                self.check_call(push_cmd, env=env)
            except subprocess.CalledProcessError:
                if plus2:
                    # Try again without CR+2
                    push_cmd[-1] = push_cmd[-1].replace(',l=Code-Review+2', '')
                    subprocess.check_call(push_cmd, env=env)
                else:
                    raise
        else:
            print('SIMULATE: '.join(push_cmd))

    def run(self, info):
        if not info.get('patch'):
            print('No patch...?')
            return
        self.clone(info['repo'])
        # TODO: investigate doing some diff/sanity check to make sure
        # the deps match updates
        self.check_call(['git', 'am'], stdin=info['patch'])
        hashtags = []
        updates = [Update.from_dict(upd) for upd in info['updates']]
        for upd in updates:
            # We use a ; instead of : because the latter can't be used in git
            # commands apparently.
            hashtags.append('%s;%s=%s' % (upd.manager[0], upd.name, upd.new))
        hashtags.extend(info['cves'])
        plus2 = self.can_autoapprove()
        # Flood control, don't overload zuul...
        gerrit.wait_for_zuul_test_gate(count=3)
        self.git_push(info['repo'], hashtags=hashtags, plus2=plus2, push=True)


def main():
    parser = argparse.ArgumentParser(description='Push patches')
    parser.add_argument('instructions', help='Filename of instructions')
    args = parser.parse_args()
    with open(args.instructions) as f:
        info = json.load(f)
    pusher = Pusher()
    pusher.run(info)


if __name__ == '__main__':
    main()
