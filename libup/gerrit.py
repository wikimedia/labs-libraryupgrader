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
import time
import urllib.parse
from typing import Dict, List

from . import session


def make_request(method, path, **kwargs):
    base = 'https://gerrit.wikimedia.org/r/'
    if 'auth' in kwargs:
        base += 'a/'
    r = session.request(method, base + path, **kwargs)
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


def query_changes(repo: str, status=None, topic=None, limit=5) -> List[Dict]:
    query = 'project:%s' % repo
    if status is not None:
        query += ' status:%s' % status
    if topic is not None:
        query += ' topic:%s' % topic
    return make_request('GET', 'changes/', params={
        'q': query,
        'n': limit,
    })


def zuul_queue_length(prefixes=('test', 'gate-and-submit')):
    # ?time is for cache busting, just like jQuery does
    r = session.get('https://integration.wikimedia.org/zuul/status.json?' + str(time.time()))
    r.raise_for_status()

    data = r.json()
    count = 0
    for pipeline in data['pipelines']:
        if not pipeline['name'].startswith(prefixes):
            continue
        for change_q in pipeline['change_queues']:
            if change_q['heads']:
                for head in change_q['heads']:
                    for patch in head:
                        if patch['jobs']:
                            count += 1

    return count


def wait_for_zuul_test_gate(count: int):
    zuul = zuul_queue_length()
    while zuul > count:
        print('test+gate-and-submit has %s jobs, waiting...' % zuul)
        time.sleep(10)
        zuul = zuul_queue_length()


def repo_branches(repo: str):
    """Get all branches for a repository"""
    encoded = urllib.parse.quote_plus(repo)
    req = make_request('GET', f'projects/{encoded}/branches/')
    branches = set()
    for item in req:
        if not item['ref'].startswith('refs/heads/'):
            continue
        branches.add(item['ref'][11:])

    return branches
