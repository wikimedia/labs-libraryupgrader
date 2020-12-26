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
import functools
import json
from markdown import markdown
import os
import re
import wikimediaci_utils

from .. import LOGS, MANAGERS, TYPES, config, db, plan
from ..data import Data
from ..model import Dependency, Dependencies, Log, Repository, Upstream

app = Flask(__name__)
app.config['BOOTSTRAP_SERVE_LOCAL'] = True
Bootstrap(app)
SEVERITIES = ['critical', 'high', 'moderate', 'low', 'info']
# TODO: find some more colors?
COLORS = ['danger', 'danger', 'warning', 'warning', 'info']
TABLE_PRESETS = {
    '/ci': ','.join([
        'composer:php-parallel-lint/php-parallel-lint',
        'composer:mediawiki/mediawiki-codesniffer',
        'composer:mediawiki/minus-x',
        'composer:mediawiki/mediawiki-phan-config',
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
        'repo_icons': repo_icons,
    }


@functools.lru_cache()
def _errors_for_icons():
    return list(Data().get_errors())


@functools.lru_cache()
def _canaries_for_icons():
    return config.repositories()['canaries']


def repo_icons(repo):
    ret = ''
    if repo in _errors_for_icons():
        ret += '❌'
    if repo in _canaries_for_icons():
        ret += '🦆'
    return ret


@app.route('/')
def index():
    count = len(set(Data().find_files()))
    return render_template('index.html', count=count)


@app.route('/r/<path:repo>')
def r(repo):
    branch = request.args.get('branch', 'master')
    db.connect()
    session = db.Session()
    repository = session.query(Repository)\
        .filter_by(name=repo, branch=branch).first()
    if repository is None:
        return make_response('Sorry, I don\'t know this repository.', 404)
    dependencies = Dependencies(session.query(Dependency)
                                .filter_by(repo=repository.name, branch=branch)
                                .all())
    logs = repository.logs[0:10]
    logs.sort(reverse=True)
    return render_template(
        'r.html',
        repo=repository,
        logs=logs,
        dependencies=dependencies,
    )


@app.route('/r')
def r_index():
    branch = request.args.get('branch', 'master')
    db.connect()
    session = db.Session()
    repos = session.query(Repository)\
        .filter_by(branch=branch)\
        .order_by(Repository.name).all()
    return render_template(
        'r_index.html',
        repos=repos,
    )


@app.route('/library')
def library_index():
    branch = request.args.get('branch', 'master')
    db.connect()
    session = db.Session()
    deps = session.query(Dependency).filter_by(branch=branch).all()
    used = defaultdict(lambda: defaultdict(set))
    for dep in deps:
        used[dep.manager][dep.name].add(dep.version)

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
    branch = request.args.get('branch', 'master')
    used = {'prod': defaultdict(set), 'dev': defaultdict(set)}

    db.connect()
    session = db.Session()
    deps = session.query(Dependency).filter_by(
        manager=manager, name=name, branch=branch).all()
    if not deps:
        return make_response('Unknown library.', 404)
    for dep in deps:
        used[dep.mode][dep.version].add(dep.repo)

    upstream = session.query(Upstream)\
        .filter_by(manager=manager, name=name)\
        .first()
    if upstream is None:
        upstream = Upstream(manager=manager, name=name, description=b'Unknown', latest='0.0.0')
    safe_version = plan.Plan(branch=branch).safe_version(manager, name)

    return render_template(
        'library.html',
        used=used,
        upstream=upstream,
        safe_version=safe_version,
    )


@app.route('/logs2/<log_id>')
def logs2(log_id):
    db.connect()
    session = db.Session()

    log = session.query(Log).filter_by(id=log_id).first()
    if log is None:
        return make_response('log_id not found', 404)

    return render_template(
        'logs2.html',
        log=log,
        repo=log.repository,
    )


@app.route('/logs/<date>/<logname>')
def logs(date, logname):
    # Input validation to prevent against directory traversal attacks
    if not re.match(r'^\d{4}-\d{2}-\d{2}$', date):
        return make_response('Invalid date', 404)
    if not re.match(r'^[A-z]{15}$', logname):
        return make_response('Invalid filename', 404)
    path = os.path.join(LOGS, date, f'{logname}.json')
    if not os.path.exists(path):
        return make_response('Can\'t find log file', 404)

    with open(path) as f:
        info = json.load(f)
    deps = Data().get_deps(info)
    return render_template(
        'logs.html',
        success=info.get('done'),
        log='\n'.join(info.get('log', [])),
        patch=info.get('patch'),
        repo=info.get('repo'),
        deps=deps,
        # FIXME: find_logs() is way too slow
        # logs=sorted(find_logs(repo))
        logs=[]
    )


@app.route('/errors')
def errors():
    branch = request.args.get('branch', 'master')
    db.connect()
    session = db.Session()
    repos = session.query(Repository)\
        .filter_by(is_error=True, branch=branch)\
        .order_by(Repository.name, Repository.branch).all()
    return render_template('errors.html', repos=repos)


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
    data = Data()
    advisories = {}
    affected = defaultdict(dict)
    for repo, info in data.get_data().items():
        if not info.get('npm-audit'):
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
        dev_all=lambda x: all(y.get('dev') for y in x),
        via=via,
    )


@app.route('/status')
def status():
    branch = request.args.get('branch', 'master')
    planner = plan.Plan(branch)
    return render_template(
        'status.html',
        status=planner.status()
    )


if __name__ == '__main__':
    app.run(debug=True)
