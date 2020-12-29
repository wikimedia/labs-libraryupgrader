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
from flask import Flask, jsonify, render_template, make_response, request
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
import json
from markdown import markdown
import os
import re
from sqlalchemy.orm import joinedload

from .. import BRANCHES, MANAGERS, plan
from ..db import sql_uri
from ..model import Advisories, Dependency, Dependencies, Log, Repository, Upstream

app = Flask(__name__)
app.config['BOOTSTRAP_SERVE_LOCAL'] = True
app.config['SQLALCHEMY_DATABASE_URI'] = sql_uri()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
Bootstrap(app)
db = SQLAlchemy(app)
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
        'markdown': markdown,
        'BRANCHES': BRANCHES,
        'gbranch': request.args.get('branch', 'master'),
    }


def repo_icons(repo: Repository):
    ret = ''
    if repo.is_error:
        ret += '❌'
    if repo.is_canary:
        ret += '🦆'
    return ret


@app.route('/')
def index():
    count = db.session.query(Repository).count()
    upstreams = db.session.query(Upstream).count()
    recent_logs = db.session.query(Log)\
        .options(joinedload(Log.repository))\
        .order_by(Log.id.desc())\
        .limit(15).all()
    return render_template('index.html', count=count, upstreams=upstreams, recent_logs=recent_logs)


@app.route('/r/<path:repo>')
def r(repo):
    branch = request.args.get('branch', 'master')
    repository = db.session.query(Repository)\
        .filter_by(name=repo, branch=branch).first()
    if repository is None:
        return make_response('Sorry, I don\'t know this repository.', 404)
    dependencies = Dependencies(repository.dependencies)
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
    repos = db.session.query(Repository)\
        .filter_by(branch=branch)\
        .order_by(Repository.name).all()
    return render_template(
        'r_index.html',
        repos=repos,
    )


@app.route('/library')
def library_index():
    branch = request.args.get('branch', 'master')
    deps = db.session.query(Dependency)\
        .join(Repository)\
        .filter(Repository.branch == branch)\
        .all()
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
    branch = request.args.get('branch', 'master')
    r_libs = request.args.get('r')
    if not r_libs:
        return 'no libs specified'
    want = []
    sp_libs = r_libs.split(',')
    for sp_lib in sp_libs:
        if ':' not in sp_lib:
            return 'no colon in lib'
        manager, libname = sp_lib.split(':', 2)
        upstream = db.session.query(Upstream).filter_by(manager=manager, name=libname).first()
        if upstream:
            want.append(upstream)
    display = []
    for repo in db.session.query(Repository).filter_by(branch=branch).all():
        deps = Dependencies(repo.dependencies)
        ret = []
        for upstream in want:
            found = False
            for mode in ['prod', 'dev']:
                dep = deps.find(Dependency(manager=upstream.manager, name=upstream.name, mode=mode))
                if dep:
                    ret.append((dep, upstream))
                    found = True
                    break
            if not found:
                ret.append((None, None))
        display.append((repo, ret))
    return render_template(
        'library_table.html',
        want=want,
        display=display,
    )


@app.route('/library/<manager>/<path:name>')
def library_(manager, name):
    if manager not in MANAGERS:
        return make_response('Unknown manager.', 404)
    branch = request.args.get('branch', 'master')
    used = {'prod': defaultdict(set), 'dev': defaultdict(set)}

    deps = db.session.query(Dependency)\
        .join(Repository)\
        .filter(Dependency.name == name, Dependency.manager == manager,
                Repository.branch == branch)\
        .all()
    if not deps:
        return make_response('Unknown library.', 404)
    for dep in deps:
        used[dep.mode][dep.version].add(dep.repository)

    upstream = db.session.query(Upstream)\
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
    log = db.session.query(Log).filter_by(id=log_id).first()
    if log is None:
        return make_response('log_id not found', 404)

    return render_template(
        'logs2.html',
        log=log,
        repo=log.repository,
    )


@app.route('/logs/<date>/<logname>')
def logs(date, logname):
    """deprecated logs, should be removed after Jan. 2021"""
    # Input validation to prevent against directory traversal attacks
    if not re.match(r'^\d{4}-\d{2}-\d{2}$', date):
        return make_response('Invalid date', 404)
    if not re.match(r'^[A-z]{15}$', logname):
        return make_response('Invalid filename', 404)
    path = os.path.join('/srv/data/logs', date, f'{logname}.json')
    if not os.path.exists(path):
        return make_response('Can\'t find log file', 404)

    with open(path) as f:
        info = json.load(f)
    return render_template(
        'logs.html',
        success=info.get('done'),
        log='\n'.join(info.get('log', [])),
        patch=info.get('patch'),
        repo=info.get('repo'),
    )


@app.route('/errors')
def errors():
    branch = request.args.get('branch', 'master')
    repos = db.session.query(Repository)\
        .filter_by(is_error=True, branch=branch)\
        .order_by(Repository.name, Repository.branch).all()
    return render_template('errors.html', repos=repos)


@app.route('/vulns/composer')
def vulns_composer():
    branch = request.args.get('branch', 'master')
    everything = db.session.query(Advisories)\
        .join(Repository)\
        .filter(Advisories.manager == "composer", Repository.branch == branch)\
        .all()
    advisories = {}

    def make_key(pkg, dtls):
        """A unique ID for each advisory"""
        if dtls.get('cve'):
            # CVE should be unique
            return dtls['cve']
        else:
            # Hopefully this combo is unique enough
            return f"{pkg}-{dtls['title']}-{dtls['link']}"

    for obj in everything:
        report = obj.get_data()
        for package, details in report.items():
            for advisory in details['advisories']:
                key = make_key(package, advisory)
                if key in advisories:
                    advisories[key]['repos'].append(obj.repository)
                else:
                    advisories[key] = {
                        'info': advisory,
                        'package': package,
                        'repos': [obj.repository]
                    }

    return render_template(
        'vulns_composer.html',
        advisories=advisories,
    )


@app.route('/vulns/npm')
def vulns_npm():
    branch = request.args.get('branch', 'master')
    everything = db.session.query(Advisories)\
        .join(Repository)\
        .filter(Advisories.manager == "npm", Repository.branch == branch)\
        .all()
    advisories = {}
    affected = defaultdict(list)
    for obj in everything:
        report = obj.get_data()
        if 'error' in report:
            # TODO: Use proper logging
            print(obj.repository.name, report)
            continue
        for a_id, a_info in report['advisories'].items():
            affected[int(a_id)].append((obj.repository, a_info))
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
        SEVERITIES=SEVERITIES,
        COLORS=COLORS,
        via=via,
    )


@app.route('/status')
def status():
    branch = request.args.get('branch', 'master')
    planner = plan.Plan(branch)
    return render_template(
        'status.html',
        status=planner.status(db.session)
    )


@app.route('/plan.json', methods=('GET', 'POST'))
def plan_json():
    """Keep in sync with HTTPPlan"""
    repo = request.args.get('repository')
    branch = request.args.get('branch')
    if not repo or not branch:
        return jsonify(
            status="error",
            error="Missing repo or branch parameter")
    repository = db.session.query(Repository).filter_by(name=repo, branch=branch).first()
    if repository is None:
        return jsonify(
            status="error",
            error="Repository not found"
        )
    posted = request.method == 'POST'
    # If it was a POST request, git pull
    planner = plan.Plan(branch, pull=posted)
    ret = planner.check(db.session, repo, repository.dependencies)
    return jsonify(
        status="ok",
        plan=ret
    )


if __name__ == '__main__':
    app.run(debug=True)
