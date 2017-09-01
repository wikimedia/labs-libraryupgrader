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
import os
import sys

import app
import docker
import mw

CODESNIFFER = 'mediawiki/mediawiki-codesniffer'
VERSIONS = ['same', 'dev-master']


def run(repo: str, ext_name: str, version: str):
    env = {
        'MODE': 'test',
        'REPO': repo,
        'PACKAGE': 'mediawiki/mediawiki-codesniffer'
    }
    if version != 'same':
        env['VERSION'] = version
    docker.run(ext_name + version, env)


def check_logs(ext_name: str, version: str):
    out = docker.logs(ext_name + version)
    try:
        data = out.split('------------')[1]
        j = json.loads(data)
        print(j)
    except (IndexError, ValueError):
        print(out)
        print('Couldnt get JSON data...')
        j = None
    docker.remove_container(ext_name + version)
    return j


def main():
    data = defaultdict(dict)
    for version in VERSIONS:
        cleanup = set()
        for info in mw.get_extension_list(CODESNIFFER):
            # Save PHPCS version
            ext = info['repo'].split('/')[-1]
            data[ext]['PHPCS'] = info['version']
            run(info['repo'], ext, version=version)
            cleanup.add(ext)
            # If more than max containers running, pause
            docker.wait_for_containers(count=docker.CONCURRENT)
        # Wait for all containers to finish...
        docker.wait_for_containers(count=0)
        for ext in cleanup:
            data[ext][version] = check_logs(ext, version)
    with open('output.json', 'w') as f:
        json.dump(data, f)
    make_index()


def make_index():
    try:
        app.make('/var/www/html/')
        print('Wrote to /var/www/html/')
    except PermissionError:
        print('Cant write to /var/www/html')
        path = os.path.dirname(__file__)
        app.make(path)
        print('Wrote to ' + path)


if __name__ == '__main__':
    if '--make-index' in sys.argv:
        make_index()
    elif len(sys.argv) > 1:
        try:
            version = sys.argv[2]
        except IndexError:
            version = 'dev-master'

        repo = sys.argv[1]
        ext = sys.argv[1].split('/')[-1]
        info = mw.repo_info(repo, CODESNIFFER)
        if not info:
            print('Doesnt have codesniffer.')
            sys.exit(1)
        run(repo, ext, version=version)
        docker.wait_for_containers(0)
        check_logs(ext, version=version)
    else:
        main()
