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

from celery import Celery
from datetime import datetime
import json
import os
import random
import string
import subprocess
import tempfile
import traceback

from . import DATA_ROOT, GIT_ROOT, MANAGERS, db, docker, gerrit, model, push, utils, ssh
from .extract import extract_dependencies

app = Celery('tasks', broker='amqp://localhost')


def _random_string():
    return ''.join(random.choice(string.ascii_letters) for _ in range(15))


@app.task
def run_check(repo_name: str, branch: str):
    db.connect()
    session = db.Session()
    repo = session.query(model.Repository).filter_by(name=repo_name, branch=branch).first()
    log_dir = utils.date_log_dir()
    rand = _random_string()
    # Update our local clone
    gerrit.ensure_clone(repo.name)
    with tempfile.TemporaryDirectory() as tmpdir:
        with utils.cd(tmpdir):
            # TODO: Move this logic out of pusher?
            pusher = push.Pusher()
            pusher.clone(repo.name, internal=True, branch=repo.branch)
            deps = extract_dependencies(repo.name, repo.branch)
            db.update_dependencies(session, repo, deps)

    try:
        docker.run(
            name=rand,
            env={},
            background=False,
            mounts={
                log_dir: '/out',
                DATA_ROOT: '/srv/data:ro',
                GIT_ROOT: f'{GIT_ROOT}:ro'
            },
            rm=True,
            # FIXME: pass branch name through
            extra_args=['libup-ng', repo.name, '/out/%s.json' % rand],
        )
    except subprocess.CalledProcessError:
        # Just print the traceback. The real check is to verify
        # that the JSON file exists.
        traceback.print_exc()
    output = os.path.join(log_dir, '%s.json' % rand)
    assert os.path.exists(output)
    # Copy it over to the "current" directory,
    # potentially overwriting existing results
    with open(output) as fr:
        fname = os.path.join(DATA_ROOT, 'current', repo.name.replace('/', '_') + '.json')
        with open(fname, 'w') as fw:
            text = fr.read()
            fw.write(text)
    data = json.loads(text)
    if data.get('patch') is not None:
        encoded_patch = data['patch'].encode()
    else:
        encoded_patch = None
    log = model.Log(
        time=utils.to_mw_time(datetime.utcnow()),
        patch=encoded_patch,
        is_error='done' not in data,
    )
    # TODO: Get this from `docker logs` instead
    log.set_text('\n'.join(data.get('log', [])))
    repo.logs.append(log)
    repo.is_error = log.is_error
    for manager in MANAGERS:
        advisories = repo.get_advisories(manager)
        new = data.get(f"{manager}-audit")
        if advisories and new:
            # Update existing row
            advisories.set_data(new)
        elif advisories and not new:
            # No more vulns, delete row
            session.delete(advisories)
        elif new and not advisories:
            advisories = model.Advisories(manager=manager)
            advisories.set_data(new)
            repo.advisories.append(advisories)
        # else: not new and not advisories:
            # pass - nothing to do

    # COMMIT everything
    session.commit()
    data['message'] = f'View logs for this commit at ' \
                      f'https://libraryupgrader2.wmcloud.org/logs2/{log.id}'
    if data.get('push') and ssh.is_key_loaded():
        with tempfile.TemporaryDirectory() as tmpdir:
            with utils.cd(tmpdir):
                pusher = push.Pusher()
                pusher.run(data)
