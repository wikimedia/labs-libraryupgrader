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


def gerrit_url(repo: str, user=None, pw=None) -> str:
    host = ''
    if user:
        if pw:
            host = user + ':' + urllib.parse.quote_plus(pw) + '@'
        else:
            host = user + '@'

    host += 'gerrit.wikimedia.org'
    return 'https://%s/r/%s.git' % (host, repo)


def ensure_package_lock():
    if not os.path.exists('package-lock.json'):
        subprocess.check_call(['npm', 'i', '--package-lock-only'])


def npm_deps():
    if not os.path.exists('package.json'):
        return None
    with open('package.json') as f:
        pkg = json.load(f)
    return {
        'deps': pkg.get('dependencies', {}),
        'dev': pkg.get('devDependencies', {}),
    }


def composer_deps():
    if not os.path.exists('composer.json'):
        return None
    with open('composer.json') as f:
        pkg = json.load(f)
    return {
        'deps': pkg.get('require', {}),
        'dev': pkg.get('require-dev', {}),
    }


def npm_audit():
    ensure_package_lock()
    try:
        subprocess.check_output(['npm', 'audit', '--json'])
        # If npm audit didn't fail, there are no vulnerable packages
        return {}
    except subprocess.CalledProcessError as e:
        try:
            return json.loads(e.output.decode())
        except json.decoder.JSONDecodeError:
            print('Error, invalid JSON, skipping')
            return {'error': e.output.decode()}


def npm_test():
    ensure_package_lock()
    subprocess.check_call(['npm', 'ci'])
    subprocess.check_call(['npm', 'test'])


def composer_test():
    subprocess.check_call(['composer', 'install'])
    subprocess.check_call(['composer', 'test'])


def git_clean():
    subprocess.check_call(['git', 'clean', '-fdx'])


def clone_commands(repo):
    url = gerrit_url(repo)
    subprocess.check_call(['git', 'clone', url, 'repo', '--depth=1'])
    os.chdir('repo')
    subprocess.check_call(['grr', 'init'])  # Install commit-msg hook


def sha1():
    return subprocess.check_output(['git', 'show-ref', 'HEAD']).decode().split(' ')[0]


def run(repo, output):
    clone_commands(repo)
    data = {
        'repo': repo,
        'sha1': sha1()
    }
    data['npm-audit'] = npm_audit()
    data['npm-deps'] = npm_deps()
    try:
        npm_test()
        data['npm-test'] = {'result': True}
    except subprocess.CalledProcessError as e:
        data['npm-test'] = {'result': False, 'error': e.output.decode()}

    git_clean()

    data['composer-deps'] = composer_deps()
    try:
        composer_test()
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
    run(args.repo, args.output)


if __name__ == '__main__':
    main()
