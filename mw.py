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

import json
import prefetch_generator
import wikimediaci_utils as ci

BLACKLIST = [
    # Per https://gerrit.wikimedia.org/r/375513
    'mediawiki/extensions/MediaWikiFarm',
]


def get_extension_list(library: str, version_match=None, exclude=[]):
    repos = set()
    skip = BLACKLIST + exclude
    for repo in ci.mw_things_repos():
        if repo not in skip:
            repos.add(repo)

    yield from filter_repo_list(sorted(repos), library, version_match=version_match)


@prefetch_generator.background()
def filter_repo_list(repos, library, version_match=None):
    for repo in repos:
        version = repo_info(repo, library)
        if version:
            # Skip codesniffer 19.0.0
            if library == 'mediawiki/mediawiki-codesniffer' and version == '19.0.0':
                continue
            if not version_match or version_match != version:
                yield {'repo': repo, 'version': version}


def repo_info(repo: str, library: str):
    if library == 'npm-audit-fix':
        return get_gerrit_file(repo, 'package.json') is not None
    phab = get_gerrit_file(repo, 'composer.json')
    if phab:
        version = phab.get('require-dev', {}).get(library)
        if version:
            return version
        if 'extra' in phab:
            suffix = library.split('/')[-1]
            version = phab['extra'].get(suffix)
            if version:
                return version
    return None


def get_gerrit_file(gerrit_name: str, path: str):
    content = ci.get_gerrit_file(gerrit_name, path)
    try:
        return json.loads(content)
    except ValueError:
        return None
