#!/usr/bin/env python3
"""
Builds a dashboard for PHPCS runs
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
import requests
import subprocess

GERRIT = 'https://gerrit.wikimedia.org/r/{0}.git'
MW_CS = 'mediawiki/mediawiki-codesniffer'
DOCKER_IMAGE = 'phpcs-dashboard'


s = requests.session()

def get_extension_list():
    r = s.get('https://www.mediawiki.org/w/api.php?action=query&list=extdistrepos&formatversion=2&format=json')
    yield from r.json()['query']['extdistrepos']['extensions']


def get_phab_file(gerrit_name, path):
    url = 'https://phabricator.wikimedia.org/r/p/{};browse/master/{}?view=raw'.format(gerrit_name, path)
    print('Fetching ' + url)
    r = s.get(url)
    try:
        return r.json()
    except:
        return None


def has_codesniffer(ext_name):
    d = get_phab_file('mediawiki/extensions/' + ext_name, 'composer.json')
    return d and d.get('require-dev', {}).get('mediawiki/mediawiki-codesniffer')

def run(ext_name, version='dev-master'):
    subprocess.check_call([
        'docker', 'run',
        '--name=' + ext_name,
        '--env', 'EXT=' + ext_name,
        '--env', 'VERSION=' + version,
        DOCKER_IMAGE,
    ])
    out = subprocess.check_output(['docker', 'logs', ext_name]).decode()
    data = out.split('------------')[1]
    try:
        j = json.loads(data)
        print(j)
    except ValueError:
        print(out)
        print('Couldnt get JSON data...')
        return None
    subprocess.check_call(['docker', 'rm', ext_name])
    return j

def main():
    data = {}
    for ext in get_extension_list():
        if has_codesniffer(ext):
            data[ext] = run(ext, version='dev-master')
        else:
            print('Skipping ' + ext)
    with open('output.json', 'w') as f:
        json.dump(data, f)

if __name__ == '__main__':
    main()
