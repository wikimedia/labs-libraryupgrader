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

import base64
import json
import prefetch_generator
import requests

BLACKLIST = [
    # Per https://gerrit.wikimedia.org/r/375513
    'mediawiki/extensions/MediaWikiFarm',
]

s = requests.session()


def get_extension_list(library: str, version_match=None):
    r = s.get('https://www.mediawiki.org/w/api.php?action=query&list=extdistrepos&formatversion=2&format=json')
    repos = set()
    for type_ in ('extensions', 'skins'):
        for ext in r.json()['query']['extdistrepos'][type_]:
            repo = 'mediawiki/' + type_ + '/' + ext
            if repo in BLACKLIST:
                continue
            repos.add(repo)

    yield from filter_repo_list(sorted(repos), library, version_match=version_match)


@prefetch_generator.background()
def filter_repo_list(repos, library, version_match=None):
    for repo in repos:
        version = repo_info(repo, library)
        if version:
            if not version_match or version_match != version:
                yield {'repo': repo, 'version': version}


def repo_info(repo: str, library: str):
    phab = get_gerrit_file(repo, 'composer.json')
    if phab:
        version = phab.get('require-dev', {}).get(library)
        if version:
            return version
    return None


def get_gerrit_file(gerrit_name: str, path: str):
    url = 'https://gerrit.wikimedia.org/r/plugins/gitiles/{}/+/master/{}?format=TEXT'.format(gerrit_name, path)
    print('Fetching ' + url)
    r = s.get(url)
    try:
        return json.loads(base64.b64decode(r.text).decode())
    except ValueError:
        return None
