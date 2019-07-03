#!/usr/bin/env python3
"""
next generation of libraryupgrader

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
import os
import subprocess
import urllib.parse


class LibraryUpgrader:

    @property
    def has_npm(self):
        return os.path.exists('package.json')

    @property
    def has_composer(self):
        return os.path.exists('composer.json')

    def check_call(self, args: list) -> str:
        res = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        # TODO: log
        print(res.stdout.decode())
        res.check_returncode()
        return res.stdout.decode()

    def gerrit_url(self, repo: str, user=None, pw=None) -> str:
        host = ''
        if user:
            if pw:
                host = user + ':' + urllib.parse.quote_plus(pw) + '@'
            else:
                host = user + '@'

        host += 'gerrit.wikimedia.org'
        return 'https://%s/r/%s.git' % (host, repo)

    def ensure_package_lock(self):
        if not os.path.exists('package-lock.json'):
            self.check_call(['npm', 'i', '--package-lock-only'])

    def npm_deps(self):
        if not self.has_npm:
            return None
        with open('package.json') as f:
            pkg = json.load(f)
        return {
            'deps': pkg.get('dependencies', {}),
            'dev': pkg.get('devDependencies', {}),
        }

    def composer_deps(self):
        if not self.has_composer:
            return None
        with open('composer.json') as f:
            pkg = json.load(f)
        ret = {
            'deps': pkg.get('require', {}),
            'dev': pkg.get('require-dev', {}),
        }
        if 'phan-taint-check-plugin' in pkg.get('extra', {}):
            ret['dev']['mediawiki/phan-taint-check-plugin'] \
                = pkg['extra']['phan-taint-check-plugin']
        return ret

    def npm_audit(self):
        if not self.has_npm:
            return {}
        self.ensure_package_lock()
        try:
            subprocess.check_output(['npm', 'audit', '--json'])
            # If npm audit didn't fail, there are no vulnerable packages
            return {}
        except subprocess.CalledProcessError as e:
            try:
                return json.loads(e.output.decode())
            except json.decoder.JSONDecodeError:
                print('Error, invalid JSON from npm audit, skipping')
                return {'error': e.output.decode()}

    def npm_test(self):
        if not self.has_npm:
            return
        self.ensure_package_lock()
        self.check_call(['npm', 'ci'])
        self.check_call(['npm', 'test'])

    def composer_test(self):
        if not self.has_composer:
            return
        self.check_call(['composer', 'install'])
        self.check_call(['composer', 'test'])

    def git_clean(self):
        self.check_call(['git', 'clean', '-fdx'])

    def clone_commands(self, repo):
        url = self.gerrit_url(repo)
        self.check_call(['git', 'clone', url, 'repo', '--depth=1'])
        os.chdir('repo')
        self.check_call(['grr', 'init'])  # Install commit-msg hook

    def sha1(self):
        return self.check_call(['git', 'show-ref', 'HEAD']).split(' ')[0]

    def run(self, repo, output):
        self.clone_commands(repo)
        data = {
            'repo': repo,
            'sha1': self.sha1()
        }
        data['npm-audit'] = self.npm_audit()
        data['npm-deps'] = self.npm_deps()
        try:
            self.npm_test()
            data['npm-test'] = {'result': True}
        except subprocess.CalledProcessError as e:
            data['npm-test'] = {'result': False, 'error': e.output.decode()}

        self.git_clean()

        data['composer-deps'] = self.composer_deps()
        try:
            self.composer_test()
            data['composer-test'] = {'result': True}
        except subprocess.CalledProcessError as e:
            data['composer-test'] = {'result': False, 'error': e.output.decode()}

        with open(output, 'w') as f:
            json.dump(data, f)


def main():
    parser = argparse.ArgumentParser(description='next generation of libraryupgrader')
    parser.add_argument('repo', help='Git repository')
    parser.add_argument('output', help='Path to output results to')
    args = parser.parse_args()
    libup = LibraryUpgrader()
    libup.run(args.repo, args.output)


if __name__ == '__main__':
    main()
