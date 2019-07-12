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
from flask import Flask, render_template, make_response, request
from flask_bootstrap import Bootstrap
import json
from markdown import markdown
import os
import wikimediaci_utils

from .. import LOGS, MANAGERS, TYPES
from ..data import Data

app = Flask(__name__)
app.config['BOOTSTRAP_SERVE_LOCAL'] = True
Bootstrap(app)
SEVERITIES = ['critical', 'high', 'moderate', 'low', 'info']
# TODO: find some more colors?
COLORS = ['danger', 'danger', 'warning', 'warning', 'info']
TABLE_PRESETS = {
    '/ci': ','.join([
        'composer:jakub-onderka/php-parallel-lint',
        'composer:mediawiki/mediawiki-codesniffer',
        'composer:mediawiki/minus-x',
        'composer:mediawiki/mediawiki-phan-config',
        'composer:mediawiki/phan-taint-check-plugin',
        'npm:grunt-eslint', 'npm:eslint-config-wikimedia',
        'npm:grunt-stylelint', 'npm:stylelint-config-wikimedia',
        'npm:grunt-jsonlint', 'npm:grunt-banana-checker'
    ])
}


@app.context_processor
def inject_to_templates():
    return {
        'sorted': sorted,
        'len': len,
    }


@app.route('/')
def index():
    count = len(set(Data().find_files()))
    return render_template('index.html', count=count)


@app.route('/r/<path:repo>')
def r(repo):
    data = Data()
    try:
        info = data.get_repo_data(repo)
    except ValueError:
        return make_response('Sorry, I don\'t know this repository.', 404)

    deps = data.get_deps(info)
    return render_template(
        'r.html',
        repo=repo,
        deps=deps,
        logs=sorted(find_logs(repo))
    )


@app.route('/r')
def r_index():
    data = Data()
    repos = list(data.get_data())
    return render_template(
        'r_index.html',
        repos=repos
    )


@app.route('/library')
def library_index():
    data = Data()
    used = defaultdict(lambda: defaultdict(set))
    for repo, info in data.get_data().items():
        deps = data.get_deps(info)
        for manager in MANAGERS:
            mdeps = deps[manager]
            for type_ in TYPES:
                for lib in mdeps[type_]:
                    used[lib.manager][lib.name].add(lib.version)

    return render_template(
        'library_index.html',
        used=used,
        table_presets=TABLE_PRESETS,
    )


@app.route('/library_table')
def library_table():
    r_libs = request.args.get('r')
    if not r_libs:
        return 'no libs specified'
    want = []
    sp_libs = r_libs.split(',')
    for sp_lib in sp_libs:
        if ':' not in sp_lib:
            return 'no colon in lib'
        manager, libname = sp_lib.split(':', 2)
        if manager not in MANAGERS:
            return 'invalid manager'
        want.append((manager, libname))
    display = OrderedDict()
    data = Data()
    for repo, info in data.get_data().items():
        deps = data.get_deps(info)
        ret = []
        for manager, w_lib in want:
            print(w_lib)
            found = False
            for type_ in TYPES:
                for lib in deps[manager][type_]:
                    if lib.name == w_lib:
                        ret.append(lib)
                        found = True
                        break
                if found:
                    break
            if not found:
                ret.append(None)
        display[repo] = ret
    print(display)
    return render_template(
        'library_table.html',
        want=want,
        display=display,
        ci_utils=wikimediaci_utils,
    )


@app.route('/library/<manager>/<path:name>')
def library_(manager, name):
    if manager not in MANAGERS:
        return make_response('Unknown manager.', 404)

    used = {'deps': defaultdict(set), 'dev': defaultdict(set)}

    found = None
    data = Data()
    for repo, info in data.get_data().items():
        deps = data.get_deps(info)
        if manager in deps:
            mdeps = deps[manager]
            for type_ in TYPES:
                for lib in mdeps[type_]:
                    if lib.name == name:
                        used[type_][lib.version].add(repo)
                        found = lib

    if not found:
        return make_response('Unknown repository.', 404)

    return render_template(
        'library.html',
        manager=manager,
        name=name,
        used=used,
        library=found,
    )


@app.route('/logs')
def logs():
    return 'Not yet implemented'


def find_logs(repo):
    for date in os.listdir(LOGS):
        if date.startswith('.'):
            continue
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
    data = Data().get_data()
    advisories = {}
    affected = defaultdict(dict)
    for repo, info in data.items():
        if not info['npm-audit']:
            continue
        if 'error' in info['npm-audit']:
            # TODO: Use proper logging
            print(repo, info['npm-audit'])
            continue
        for a_id, a_info in info['npm-audit']['advisories'].items():
            affected[int(a_id)][repo] = a_info
            if a_id not in advisories:
                advisories[a_id] = a_info

    advisories = OrderedDict(sorted(
        advisories.items(),
        key=lambda x: (SEVERITIES.index(x[1]['severity']), x[0])
    ))

    def via(findings):
        ret = set()
        for finding in findings:
            for path in finding['paths']:
                ret.add(path.split('>', 1)[0])

        return sorted(ret)

    return render_template(
        'vulns_npm.html',
        advisories=advisories,
        affected=affected,
        markdown=markdown,
        SEVERITIES=SEVERITIES,
        COLORS=COLORS,
        dev_all=lambda x: all(y['dev'] for y in x),
        via=via,
    )


if __name__ == '__main__':
    app.run(debug=True)
