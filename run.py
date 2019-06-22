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

from datetime import datetime
import json
import os
import random
import string
import wikimediaci_utils as ci

import docker

CODESNIFFER = 'mediawiki/mediawiki-codesniffer'
VERSIONS = ['same', 'dev-master']


def _random_string():
    return ''.join(random.choice(string.ascii_letters) for _ in range(15))


def run(repo: str, log_dir: str):
    rand = _random_string()
    docker.run(
        name=rand,
        env={},
        mounts={log_dir: '/out'},
        rm=True,
        extra_args=[repo, '/out/%s.json' % rand],
        entrypoint='/usr/bin/libup-ng'
    )
    return rand


def main():
    data = {}
    check = []
    log_dir = os.path.join('/srv/logs', datetime.utcnow().strftime('%Y-%m-%d'))
    if not os.path.isdir(log_dir):
        os.mkdir(log_dir)
    for repo in sorted(ci.mw_things_repos()):
        print(repo)
        check.append(run(repo, log_dir))
        # If more than max containers running, pause
        docker.wait_for_containers(count=docker.CONCURRENT)

    # Wait for all containers to finish...
    docker.wait_for_containers(count=0)
    for ps_name in check:
        fname = os.path.join(log_dir, '%s.json' % ps_name)
        if os.path.exists(fname):
            with open(fname) as f:
                rdata = json.load(f)
            data[rdata['repo']] = rdata
        else:
            # ????
            pass

    with open('output.json', 'w') as f:
        json.dump(data, f)


if __name__ == '__main__':
    main()
