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
import subprocess

from . import shell
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

    def git_push(self, hashtags: list, plus2=False, push=False):
        # TODO: add ssh remote
        per = '%topic=bump-dev-deps'
        for hashtag in hashtags:
            per += ',t=' + hashtag
        if plus2:
            per += ',l=Code-Review+2'
        push_cmd = ['git', 'push', 'origin',
                    'HEAD:refs/for/master' + per]
        if push:
            try:
                self.check_call(push_cmd)
            except subprocess.CalledProcessError:
                if plus2:
                    # Try again without CR+2
                    push_cmd[-1] = push_cmd[-1].replace(',l=Code-Review+2', '')
                    subprocess.check_call(push_cmd)
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
            hashtags.append('%s:%s=%s' % (upd.manager[0], upd.name, upd.new))
        hashtags.extend(info['cves'])
        plus2 = self.can_autoapprove()
        self.git_push(hashtags=hashtags, plus2=plus2, push=False)


def main():
    parser = argparse.ArgumentParser(description='Push patches')
    parser.add_argument('instructions', help='Filename of instructions')
    args = parser.parse_args()
    pusher = Pusher()
    pusher.run(args.instructions)


if __name__ == '__main__':
    main()
