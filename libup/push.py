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

import subprocess
import urllib.parse

from . import GERRIT_USER, SSH_AUTH_SOCK, config, gerrit, shell, utils
from .model import Log, Repository


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
    '.stylelintrc.json',
    '.stylelintrc => .stylelintrc.json',
    'CODE_OF_CONDUCT.md',
    '.gitignore',
    'Gruntfile.js',
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
                f'HEAD:refs/for/{options["branch"]}' + per]

    def git_push(self, repo: Repository, hashtags: list, message='', plus2=False, push=False):
        options = {
            'repo': repo.name,
            'hashtags': hashtags,
            'message': message,
            'branch': repo.get_git_branch(),
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

    def is_latest(self, log: Log, repo: Repository) -> bool:
        """Make sure this is the latest log for this repository"""
        logs = repo.logs
        if logs[-1].id != log.id:
            print(f"Newer run available: we are {log.id} but {logs[-1].id} exists, skipping")
            return False
        return True

    def run(self, log: Log, repo: Repository):
        patch = log.get_patch()
        if not patch:
            print('No patch...?')
            return
        # Update our local clone
        gerrit.ensure_clone(repo.name, repo.get_git_branch())
        self.clone(repo.name, branch=repo.get_git_branch(), internal=True)
        current_sha1 = self.git_sha1(branch=repo.get_git_branch())
        if current_sha1 != log.sha1:
            # The repo has been updated in the meantime, don't push
            print(f"Created patch at {log.sha1}, now at {current_sha1}, skipping")
            return
        open_changes = gerrit.query_changes(
            repo=repo.name, status='open', topic='bump-dev-deps',
            branch=repo.get_git_branch(),
        )
        if open_changes:
            print(f"{repo.name} ({repo.branch}, git: {repo.get_git_branch()}) has other open changes, skipping push")
            return
        # TODO: investigate doing some diff/sanity check to make sure
        # the deps match updates
        self.check_call(['git', 'am'], stdin=patch)
        hashtags = log.get_hashtags()
        message = f'View logs for this commit at https://libraryupgrader2.wmcloud.org/logs2/{log.id}'
        plus2 = self.can_autoapprove()
        # We're definitely going to push now. Do some final sanity checks
        if not self.is_latest(log, repo):
            return
        push = config.should_push()
        self.git_push(repo, hashtags=hashtags, message=message,
                      plus2=plus2, push=push)
