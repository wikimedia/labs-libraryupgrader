#!/usr/bin/env python3
"""
Shows a dashboard for PHPCS runs
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
import jinja2
import json
import os

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), 'templates')


def render_template(fname, **kwargs):
    with open(os.path.join(TEMPLATE_DIR, fname)) as f:
        temp = jinja2.Template(f.read())
    return temp.render(**kwargs)


def read():
    with open('output.json') as f:
        data = json.load(f)
    new = defaultdict(dict)
    for ext in data:
        for version in data[ext]:
            info = data[ext][version]
            if not info:
                new[ext][version] = 'Error'
            else:
                new[ext][version] = sum(info['totals'].values())

    return new


def index():
    return render_template('index.html', data=read())


if __name__ == '__main__':
    with open('index.html', 'w') as f:
        f.write(index())
    print('Wrote to index.html')
