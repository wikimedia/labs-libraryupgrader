"""
Copyright (C) 2019 Kunal Mehta <legoktm@member.fsf.org>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

from collections import defaultdict, OrderedDict
from flask import Flask, render_template
from flask_bootstrap import Bootstrap
import json
from markdown import markdown
import os
import re

LOGS = '/srv/logs/'
RE_CODE = re.compile('`(.*?)`')

app = Flask(__name__)
app.config['BOOTSTRAP_SERVE_LOCAL'] = True
Bootstrap(app)
SEVERITIES = ['critical', 'high', 'moderate', 'low', 'info']
# TODO: find some more colors?
COLORS = ['danger', 'danger', 'warning', 'warning', 'info']


def get_data():
    path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'output.json')
    with open(path) as f:
        return json.load(f)


@app.route('/')
def index():
    count = len(get_data())
    return render_template('index.html', count=count)


@app.route('/r/<path:repo>')
def r(repo):
    # FIXME: do some validation on repo name
    return render_template('r.html', repo=repo, logs=find_logs(repo))


@app.route('/logs')
def logs():
    return 'Not yet implemented'


def find_logs(repo):
    for date in os.listdir(LOGS):
        path = os.path.join(LOGS, date)
        files = os.listdir(path)
        old_repo = repo.replace('/', '_')
        yield from [os.path.join(path, x)
                    for x in files if x.startswith(old_repo)]
        yield from _new_log_search(
            repo,
            [os.path.join(path, x)
             for x in files if x.endswith('.json')]
        )


def _new_log_search(repo, files):
    for fname in files:
        with open(fname) as f:
            if json.load(f)['repo'] == repo:
                yield fname


@app.route('/vulns/npm')
def vulns_npm():
    data = get_data()
    advisories = {}
    affected = defaultdict(dict)
    for repo, info in data.items():
        if not info['npm-audit']:
            continue
        for a_id, a_info in info['npm-audit']['advisories'].items():
            affected[int(a_id)][repo] = a_info
            if a_id not in advisories:
                advisories[a_id] = a_info

    advisories = OrderedDict(sorted(
        advisories.items(),
        key=lambda x: SEVERITIES.index(x[1]['severity'])
    ))

    def via(findings):
        ret = set()
        for finding in findings:
            for path in finding['paths']:
                ret.add(path.split('>', 1)[0])

        return ', '.join(sorted(ret))

    return render_template(
        'vulns_npm.html',
        advisories=advisories,
        affected=affected,
        markdown=markdown,
        SEVERITIES=SEVERITIES,
        COLORS=COLORS,
        sorted=sorted,
        len=len,
        dev_all=lambda x: all(y['dev'] for y in x),
        via=via,
    )


if __name__ == '__main__':
    app.run(debug=True)
