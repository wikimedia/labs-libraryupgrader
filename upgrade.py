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

import datetime
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
    'mediawiki/oauthclient-php',
    'mediawiki/tools/codesniffer',
    'mediawiki/tools/minus-x',
    'mediawiki/tools/phan',
    'mediawiki/tools/phan/SecurityCheckPlugin',
    'mediawiki/tools/phpunit-patch-coverage',
    'oojs',
    'oojs/ui',
    'php-session-serializer',
    'purtle',
    'testing-access-wrapper',
    'unicodejs',
    'utfnormal',
    'wikimedia/lucene-explain-parser',
    'wikimedia/textcat',
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


def get_library_list():
    yield from gerrit.list_projects('mediawiki/libs/')
    yield from OTHER_LIBRARIES


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
            mw.get_extension_list(library, version_match=version, exclude=CANARIES)
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
    log_dir = os.path.join('logs', datetime.datetime.utcnow().strftime('%Y-%m-%d'))
    if not os.path.isdir(log_dir):
        os.mkdir(log_dir)
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
