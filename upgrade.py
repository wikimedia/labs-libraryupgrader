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

import docker
import gerrit
import mw


GERRIT_USER = 'libraryupgrader'
CANARIES = [
    'mediawiki/extensions/Linter',
    'mediawiki/extensions/MassMessage',
    'mediawiki/extensions/VisualEditor',
    'mediawiki/skins/MonoBook',
    'oojs/ui',
]
BLACKLIST = [
    # Per https://gerrit.wikimedia.org/r/375513
    'mediawiki/extensions/MediaWikiFarm',
]
# Gerrit repos not under mediawiki/libs/
OTHER_LIBRARIES = [
    'AhoCorasick',
    'CLDRPluralRuleParser',
    'HtmlFormatter',
    'IPSet',
    'RelPath',
    'RunningStat',
    'VisualEditor/VisualEditor',
    'WrappedString',
    'at-ease',
    'base-convert',
    'cdb',
    'css-sanitizer',
    'integration/docroot',
    'labs/tools/stewardbots',
    'oojs',
    'oojs/ui',
    'php-session-serializer',
    'purtle',
    'testing-access-wrapper',
    'unicodejs',
    'utfnormal',
]


def run(repo: str, library: str, version: str, pw: str) -> str:
    env = {
        'MODE': 'upgrade',
        'REPO': repo,
        'PACKAGE': library,
        'VERSION': version,
        'GERRIT_USER': GERRIT_USER,
        'GERRIT_PW': pw,
    }
    name = repo.split('/')[-1] + library.split('/')[-1]
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
        if info['repo'] not in BLACKLIST:
            yield info['repo']


def get_library_list():
    yield from gerrit.list_projects('mediawiki/libs/')
    yield from OTHER_LIBRARIES


def main():
    if len(sys.argv) < 3:
        print('Usage: upgrade.py library version repo')
        sys.exit(1)
    library = sys.argv[1]
    version = sys.argv[2]
    repo = sys.argv[3]
    pw = getpass.getpass('HTTP Password for %s: ' % GERRIT_USER)
    if repo == 'extensions':
        repos = preprocess_filter(
            mw.get_extension_list(library, version_match=version)
        )
    elif repo == 'canaries':
        repos = preprocess_filter(
            mw.filter_repo_list(CANARIES, library, version_match=version)
        )
    elif repo == 'libraries':
        repos = preprocess_filter(
            mw.filter_repo_list(get_library_list(), library, version_match=version)
        )
    else:
        repos = [repo]
    processed = set()
    for repo in repos:
        name = run(repo, library, version, pw)
        processed.add(name)
        docker.wait_for_containers(count=2)

    docker.wait_for_containers(0)
    for name in processed:
        logs = get_safe_logs(name, pw)
        with open(os.path.join('logs', name + '.log'), 'w') as f:
            f.write(logs)
        print('Saved logs to %s.log' % name)
        docker.remove_container(name)


if __name__ == '__main__':
    main()
