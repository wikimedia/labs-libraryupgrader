#!/usr/bin/env python3
"""
Common functions for Gerrit things
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
import requests
import time

s = requests.Session()


def make_request(method, path, **kwargs):
    base = 'https://gerrit.wikimedia.org/r/'
    if 'auth' in kwargs:
        base += 'a/'
    r = s.request(method, base + path, **kwargs)
    r.raise_for_status()

    return json.loads(r.text[4:])


def list_projects(prefix=None):
    params = {}
    if prefix is not None:
        params['p'] = prefix
    data = make_request('GET', 'projects/', params=params)
    repos = set()
    for repo, info in data.items():
        if info['state'] != 'ACTIVE':
            continue
        repos.add(repo)

    yield from sorted(repos)


def zuul_queue_length(q='gate-and-submit'):
    # ?time is for cache busting, just like jQuery does
    r = s.get('https://integration.wikimedia.org/zuul/status.json?' + str(time.time()))
    r.raise_for_status()

    data = r.json()
    for pipeline in data['pipelines']:
        if pipeline['name'] != 'gate-and-submit':
            continue
        count = 0
        for change_q in pipeline['change_queues']:
            if change_q['heads']:
                count += sum(len(head) for head in change_q['heads'])

        return count

    # We never found the gate-and-submit queue?
    return 0


def wait_for_zuul_gate(count: int):
    zuul = zuul_queue_length()
    while zuul > count:
        print('gate-and-submit has %s jobs, waiting...' % zuul)
        time.sleep(10)
        zuul = zuul_queue_length()
