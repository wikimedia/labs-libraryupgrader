"""
Copyright (C) 2019 Kunal Mehta <legoktm@debian.org>

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
from flask_sqlalchemy import SQLAlchemy
from markdown import markdown
from sqlalchemy.orm import joinedload
from sqlalchemy.sql.expression import func

from . import MANAGERS, config, plan, utils
from .db import sql_uri
from .model import Advisories, Dependency, Dependencies, Log, Repository, Upstream

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = sql_uri()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
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
        'markdown': markdown,
        'branches': config.branches(),
        'gbranch': request_branch(),
    }


def request_branch():
    branch = utils.normalize_branch(request.args.get('branch', 'main'))
    branches = config.branches()
    if branch not in branches:
        # Default to main
        branch = branches[0]
    return branch


@app.get('/')
def index():
    count = db.session.query(Repository).count()
    upstreams = db.session.query(Upstream).count()
    recent_logs = db.session.query(Log)\
        .options(joinedload(Log.repository))\
        .order_by(Log.id.desc())\
        .limit(15).all()
    return render_template('index.html', count=count, upstreams=upstreams, recent_logs=recent_logs)


@app.get('/credits')
def credits_():
    return render_template('credits.html')


@app.get('/r/<path:repo>')
def r(repo):
    branch = request_branch()
    repository = db.session.query(Repository)\
        .filter_by(name=repo, branch=branch)\
        .options(joinedload(Repository.dependencies))\
        .first()
    if repository is None:
        return make_response('Sorry, I don\'t know this repository.', 404)
    dependencies = Dependencies(repository.dependencies)
    logs = db.session.query(Log)\
        .filter_by(repo_id=repository.id)\
        .order_by(Log.id.desc())\
        .limit(10).all()
    return render_template(
        'r.html',
        repo=repository,
        logs=logs,
        dependencies=dependencies,
    )


@app.get('/r')
def r_index():
    branch = request_branch()
    repos = db.session.query(Repository)\
        .filter_by(branch=branch)\
        .order_by(Repository.name).all()
    return render_template(
        'r_index.html',
        repos=repos,
    )


@app.get('/library')
def library_index():
    branch = request_branch()
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


@app.get('/library_table')
def library_table():
    branch = request_branch()
    r_libs = request.args.get('r')
    if not r_libs:
        return 'no libs specified'
    want = []
    sp_libs = r_libs.split(',')
    for sp_lib in sp_libs:
        if ':' not in sp_lib:
            return 'no colon in lib'
        manager, libname = sp_lib.split(':', 2)
        # TODO: batch this query
        upstream = db.session.query(Upstream).filter_by(manager=manager, name=libname).first()
        if upstream:
            want.append(upstream)
    display = []
    repos = db.session.query(Repository)\
        .filter_by(branch=branch)\
        .options(joinedload(Repository.dependencies))\
        .all()
    for repo in repos:
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


@app.get('/library/<manager>/<path:name>')
def library_(manager, name):
    if manager not in MANAGERS:
        return make_response('Unknown manager.', 404)
    branch = request_branch()
    used = {'prod': defaultdict(set), 'dev': defaultdict(set)}

    deps = db.session.query(Dependency)\
        .join(Repository)\
        .filter(Dependency.name == name, Dependency.manager == manager,
                Repository.branch == branch)\
        .options(joinedload(Dependency.repository))\
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


@app.get('/logs2/<log_id>')
def logs2(log_id):
    log = db.session.query(Log)\
        .filter_by(id=log_id)\
        .options(joinedload(Log.repository))\
        .first()
    if log is None:
        return make_response('log_id not found', 404)

    return render_template(
        'logs2.html',
        log=log,
        repo=log.repository,
    )


@app.get('/errors')
def errors():
    branch = request_branch()
    repos = db.session.query(Repository)\
        .filter_by(is_error=True, branch=branch)\
        .order_by(Repository.name, Repository.branch).all()
    return render_template('errors.html', repos=repos)


@app.get('/vulns/composer')
def vulns_composer():
    branch = request_branch()
    everything = db.session.query(Advisories)\
        .join(Repository)\
        .filter(Advisories.manager == "composer", Repository.branch == branch)\
        .options(joinedload(Advisories.repository))\
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


@app.get('/vulns/npm')
def vulns_npm():
    branch = request_branch()
    everything = db.session.query(Advisories)\
        .join(Repository)\
        .filter(Advisories.manager == "npm", Repository.branch == branch)\
        .options(joinedload(Advisories.repository))\
        .all()
    advisories = {}
    for obj in everything:
        report = obj.get_data()
        if 'error' in report:
            # TODO: Use proper logging
            print(obj.repository.name, report)
            continue
        if report.get("auditReportVersion") != 2:
            # old npm v6 report
            continue
        for info in report["vulnerabilities"].values():
            for via in info["via"]:
                if type(via) == dict:
                    if via["source"] in advisories:
                        advisories[via["source"]]["repos"].append(obj.repository)
                    else:
                        advisories[via["source"]] = {
                            "info": via,
                            "repos": [obj.repository],
                        }

    advisories = OrderedDict(sorted(
        advisories.items(),
        key=lambda x: (SEVERITIES.index(x[1]["info"]['severity']), x[0])
    ))

    return render_template(
        'vulns_npm.html',
        advisories=advisories,
        SEVERITIES=SEVERITIES,
        COLORS=COLORS,
    )


@app.get('/status')
def status():
    branch = request_branch()
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
    branch = utils.normalize_branch(branch)
    repository = db.session.query(Repository)\
        .filter_by(name=repo, branch=branch)\
        .options(joinedload(Repository.dependencies))\
        .first()
    branches = config.branches()
    if repository is None:
        return jsonify(
            status="error",
            error="Repository not found"
        )
    if branch not in branches:
        return jsonify(
            status="error",
            error="Invalid branch specified. Choose one of: " + ', '.join(branches)
        )
    posted = request.method == 'POST'
    # If it was a POST request, git pull
    planner = plan.Plan(branch, pull=posted)
    ret = planner.check(db.session, repo, repository.dependencies)
    return jsonify(
        status="ok",
        plan=ret
    )


@app.route('/metrics')
def metrics():
    max_log = db.session.query(func.max(Log.id)).scalar()
    resp = make_response(render_template('metrics.prom', max_log=max_log))
    resp.headers['content-type'] = 'text/plain'
    return resp


if __name__ == '__main__':
    app.run(debug=True)
