#!/usr/bin/env python3
"""
Upgrades libraries!
Copyright (C) 2017 Kunal Mehta <legoktm@member.fsf.org>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import getpass
import os
import sys

from . import date_log_dir
from . import docker, gerrit, mw


GERRIT_USER = 'libraryupgrader'


def run(repo: str, library: str, version: str, pw: str) -> str:
    env = {
        'MODE': 'upgrade',
        'REPO': repo,
        'PACKAGE': library,
        'VERSION': version,
        'GERRIT_USER': GERRIT_USER,
        'GERRIT_PW': pw,
    }
    name = repo.replace('/', '_') + library.split('/')[-1]
    docker.run(name, env)

    return name


def get_safe_logs(name: str, pw: str) -> str:
    logs = docker.logs(name)
    # Prevent the password from accidentally leaking
    if pw:
        logs = logs.replace(pw, '<password>')

    return logs


def preprocess_filter(gen):
    for info in gen:
        yield info['repo']


def main():
    if len(sys.argv) < 3:
        print('Usage: upgrade.py library version repo [limit]')
        sys.exit(1)
    library = sys.argv[1]
    version = sys.argv[2]
    repo = sys.argv[3]
    try:
        limit = int(sys.argv[4])
    except IndexError:
        limit = None

    pw = getpass.getpass('HTTP Password for %s: ' % GERRIT_USER)
    if repo == 'extensions':
        repos = preprocess_filter(
            mw.get_extension_list(library, version_match=version, exclude=mw.CANARIES)
        )
    elif repo == 'canaries':
        repos = preprocess_filter(
            mw.filter_repo_list(mw.CANARIES, library, version_match=version)
        )
    elif repo == 'libraries':
        repos = preprocess_filter(
            mw.filter_repo_list(mw.get_library_list(), library, version_match=version)
        )
    else:
        repos = [repo]
    processed = set()
    log_dir = date_log_dir()
    for repo in repos:
        name = run(repo, library, version, pw)
        processed.add(name)
        docker.wait_for_containers(count=0)
        logs = get_safe_logs(name, pw)
        with open(os.path.join(log_dir, name + '.log'), 'w') as f:
            f.write(logs)
        print('Saved logs to %s.log' % name)
        docker.remove_container(name)
        gerrit.wait_for_zuul_test_gate(count=3)
        if limit is not None and len(processed) > limit:
            print('Passed limit of %s, breaking' % limit)
            break


if __name__ == '__main__':
    main()