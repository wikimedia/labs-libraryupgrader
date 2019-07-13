#!/usr/bin/env python3
"""
Common functions for MediaWiki stuff things.
Copyright (C) 2017-2018 Kunal Mehta <legoktm@member.fsf.org>

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

import wikimediaci_utils as ci

from . import gerrit
from .data import Data


BLACKLIST = [
    # Per https://gerrit.wikimedia.org/r/375513
    'mediawiki/extensions/MediaWikiFarm',
]

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
    'mediawiki/services/parsoid',
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


def get_everything(exclude=BLACKLIST):
    for x in sorted(ci.mw_things_repos()):
        if x not in exclude:
            yield x
    for x in sorted(get_library_list()):
        if x not in exclude:
            yield x


def get_library_list():
    yield from gerrit.list_projects('mediawiki/libs/')
    yield from OTHER_LIBRARIES


def get_extension_list(library: str, version_match=None, exclude=[]):
    repos = set()
    skip = BLACKLIST + exclude
    for repo in ci.mw_things_repos():
        if repo not in skip:
            repos.add(repo)

    yield from filter_repo_list(sorted(repos), library, version_match=version_match)


def filter_repo_list(repos, library, version_match=None):
    for repo in repos:
        version = repo_info(repo, library)
        if version:
            # Skip codesniffer 19.x.0
            if library == 'mediawiki/mediawiki-codesniffer' and version.startswith('19.'):
                continue
            elif library == 'mediawiki/mediawiki-phan-config' and version == '0.3.0':
                # Requires manual intervention to upgrade
                continue
            if not version_match or version_match != version:
                yield {'repo': repo, 'version': version}


def repo_info(repo: str, library: str):
    data = Data()
    try:
        info = data.get_repo_data(repo)
    except ValueError:
        return None
    deps = data.get_deps(info)

    if library == 'npm-audit-fix':
        # Any npm deps
        return bool(deps['npm']['dev'] or deps['npm']['deps'])
    for lib in (deps['composer']['deps'] + deps['composer']['dev']):
        if lib.name == library:
            return lib.version
    return None
