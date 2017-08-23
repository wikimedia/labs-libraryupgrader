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
import shutil

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), 'templates')


def render_template(fname, **kwargs):
    with open(os.path.join(TEMPLATE_DIR, fname)) as f:
        temp = jinja2.Template(f.read())
    return temp.render(**kwargs)


def read_raw():
    with open('output.json') as f:
        return json.load(f)


def read_by_sniff(version='dev-master'):
    new = defaultdict(lambda: defaultdict(int))
    data = read_raw()
    for ext in data:
        info = data[ext][version]
        if not info:
            continue
        for name, finfo in info['files'].items():
            for message in finfo['messages']:
                sniff = message['source']
                new[sniff][ext] += 1

    return new


def read_by_ext(version='dev-master'):
    new = {}
    data = read_raw()
    for ext in data:
        info = data[ext][version]
        count = defaultdict(int)
        if not info:
            continue
        for fname, finfo in info['files'].items():
            for message in finfo['messages']:
                count[message['source']] += 1
        new[ext] = count

    return new


def read():
    new = defaultdict(dict)
    data = read_raw()
    for ext in data:
        for version in data[ext]:
            info = data[ext][version]
            if version == 'PHPCS':
                new[ext][version] = info
            elif not info:
                new[ext][version] = 'Error'
            else:
                new[ext][version] = info['totals']['errors'] + info['totals']['warnings']

    return new


def index():
    return render_template('index.html', data=read())


def make(path):
    with open(os.path.join(path, 'index.html'), 'w') as f:
        f.write(render_template('index.html', data=read()))

    by_ext = read_by_ext()
    ext_path = os.path.join(path, 'extensions')
    if not os.path.isdir(ext_path):
        os.mkdir(ext_path)

    for ext, data in by_ext.items():
        with open(os.path.join(ext_path, ext + '.html'), 'w') as f:
            f.write(render_template('extension.html', ext=ext, data=data))

    by_sniff = read_by_sniff()
    sniff_path = os.path.join(path, 'sniffs')
    if os.path.isdir(sniff_path):
        shutil.rmtree(sniff_path)
    os.mkdir(sniff_path)

    for sniff, data in by_sniff.items():
        with open(os.path.join(sniff_path, sniff + '.html'), 'w') as f:
            f.write(render_template('sniff.html', sniff=sniff, data=data))


if __name__ == '__main__':
    with open('index.html', 'w') as f:
        f.write(index())
    print('Wrote to index.html')
