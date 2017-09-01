#!/usr/bin/env python3
"""
Common functions for MediaWiki stuff things.
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

import prefetch_generator
import requests


s = requests.session()


@prefetch_generator.background()
def get_extension_list(library: str, version_match=None):
    r = s.get('https://www.mediawiki.org/w/api.php?action=query&list=extdistrepos&formatversion=2&format=json')
    for type_ in ('extensions', 'skins'):
        for ext in r.json()['query']['extdistrepos'][type_]:
            repo = 'mediawiki/' + type_ + '/' + ext
            version = repo_info(repo, library)
            if version:
                if not version_match or version_match != version:
                    yield {'repo': repo, 'version': version}


def repo_info(repo: str, library: str):
    phab = get_phab_file(repo, 'composer.json')
    if phab:
        version = phab.get('require-dev', {}).get(library)
        if version:
            return version
    return None


def get_phab_file(gerrit_name: str, path: str):
    url = 'https://phabricator.wikimedia.org/r/p/{};browse/master/{}?view=raw'.format(gerrit_name, path)
    # url = 'https://raw.githubusercontent.com/wikimedia/{}/master/{}'.format(gerrit_name.replace('/', '-'), path)
    print('Fetching ' + url)
    r = s.get(url)
    try:
        return r.json()
    except:
        return None
