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

import json
import os
import sys

import docker
import mw


if os.path.exists('config.json'):
    with open('config.json') as f:
        CONFIG = json.load(f)
else:
    CONFIG = {}

CANARIES = [
    'mediawiki/extensions/Linter',
    'mediawiki/extensions/MassMessage',
    'mediawiki/extensions/VisualEditor',
    'mediawiki/skins/MonoBook',
    'oojs/ui',
]


def run(repo, library, version):
    env = {
        'MODE': 'upgrade',
        'REPO': repo,
        'PACKAGE': library,
        'VERSION': version,
        'GERRIT_USER': CONFIG.get('GERRIT_USER'),
        'GERRIT_PW': CONFIG.get('GERRIT_PW'),
    }
    name = repo.split('/')[-1] + library.split('/')[-1]
    docker.run(name, env)

    return name


def get_safe_logs(name):
    logs = docker.logs(name)
    if CONFIG.get('GERRIT_PW'):
        # Prevent the password from accidentally leaking
        logs = logs.replace(CONFIG.get('GERRIT_PW'), '<password>')

    return logs


def get_extension_list(library, version_match):
    for info in mw.get_extension_list(library, version_match):
        yield info['repo']


def main():
    if len(sys.argv) < 3:
        print('Usage: upgrade.py library version repo')
        sys.exit(1)
    library = sys.argv[1]
    version = sys.argv[2]
    repo = sys.argv[3]
    if repo == 'extensions':
        repos = get_extension_list(library, version_match=version)
    elif repo == 'canaries':
        repos = CANARIES
    else:
        repos = [repo]
    processed = set()
    for repo in repos:
        name = run(repo, library, version)
        processed.add(name)
        docker.wait_for_containers(count=2)

    docker.wait_for_containers(0)
    for name in processed:
        logs = get_safe_logs(name)
        with open(os.path.join('logs', name + '.log'), 'w') as f:
            f.write(logs)
        print('Saved logs to %s.log' % name)
        docker.remove_container(name)


if __name__ == '__main__':
    main()
