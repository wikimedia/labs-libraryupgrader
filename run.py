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

from collections import defaultdict
import json
import requests
import subprocess
import sys
import time

CONCURRENT = 5
DOCKER_IMAGE = 'phpcs-dashboard'
VERSIONS = ['same', 'dev-master']


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


def run(ext_name, version):
    args = [
        'docker', 'run',
        '--name=' + ext_name + version,
        '--env', 'EXT=' + ext_name,
    ]
    if version != 'same':
        args.extend(['--env', 'VERSION=' + version])
    args.extend(['-d', DOCKER_IMAGE])
    subprocess.check_call(args)


def check_logs(ext_name, version):
    out = subprocess.check_output(['docker', 'logs', ext_name + version]).decode()
    data = out.split('------------')[1]
    try:
        j = json.loads(data)
        print(j)
    except ValueError:
        print(out)
        print('Couldnt get JSON data...')
        j = None
    subprocess.check_call(['docker', 'rm', ext_name + version])
    return j


def get_running_containers():
    out = subprocess.check_output(['docker', 'ps', '-q']).decode().strip()
    if not out:
        return []
    return out.split('\n')


def wait_for_containers(count):
    while len(get_running_containers()) > count:
        print('Waiting...')
        time.sleep(2)


def main():
    for version in VERSIONS:
        data = defaultdict(dict)
        cleanup = set()
        for ext in get_extension_list():
            if has_codesniffer(ext):
                run(ext, version=version)
                cleanup.add(ext)
            else:
                print('Skipping ' + ext)
            # If more than max containers running, pause
            wait_for_containers(count=CONCURRENT)
        # Wait for all containers to finish...
        wait_for_containers(count=0)
        for ext in cleanup:
            data[ext][version] = check_logs(ext, version)
        with open('output.json', 'w') as f:
            json.dump(data, f)

if __name__ == '__main__':
    if len(sys.argv) > 1:
        try:
            version = sys.argv[2]
        except IndexError:
            version = 'dev-master'
        run(sys.argv[1], version=version)
        wait_for_containers(0)
        check_logs(sys.argv[1], version=version)
    else:
        main()
