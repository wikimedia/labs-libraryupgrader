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


@app.route('/vulns/npm')
def vulns_npm():
    data = get_data()
    advisories = {}
    affected = defaultdict(list)
    for repo, info in data.items():
        if not info['npm-audit']:
            continue
        for a_id, a_info in info['npm-audit']['advisories'].items():
            affected[int(a_id)].append(repo)
            if a_id not in advisories:
                advisories[a_id] = a_info

    advisories = OrderedDict(sorted(
        advisories.items(),
        key=lambda x: SEVERITIES.index(x[1]['severity'])
    ))
    return render_template(
        'vulns_npm.html',
        advisories=advisories,
        affected=affected,
        markdown=markdown,
        SEVERITIES=SEVERITIES,
        COLORS=COLORS,
        sorted=sorted,
        len=len,
    )


if __name__ == '__main__':
    app.run(debug=True)
