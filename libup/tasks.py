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
import subprocess
import sys
import tempfile
import traceback

from . import GIT_ROOT, MANAGERS, db, docker, gerrit, model, push, utils, ssh
from .extract import extract_dependencies

app = Celery('tasks', broker='amqp://localhost')


@app.task
def run_check(repo_name: str, branch: str):
    session = db.Session()
    repo = session.query(model.Repository).filter_by(name=repo_name, branch=branch).first()
    # Update our local clone
    gerrit.ensure_clone(repo.name)
    with tempfile.TemporaryDirectory() as tmpdir:
        with utils.cd(tmpdir):
            # TODO: Move this logic out of pusher?
            pusher = push.Pusher(branch=repo.branch)
            pusher.clone(repo.name, internal=True, branch=repo.branch)
            deps = extract_dependencies(repo)
            db.update_dependencies(session, repo, deps)

    container_name = repo.name.split('/')[-1] + '-' + repo.branch
    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            docker.run(
                name=container_name,
                env={},
                background=False,
                mounts={
                    tmpdir: '/out',
                    GIT_ROOT: f'{GIT_ROOT}:ro'
                },
                rm=True,
                # FIXME: pass branch name through
                extra_args=['libup-ng', repo.name, '/out/output.json'],
            )
        except subprocess.CalledProcessError:
            # Just print the traceback. The real check is to verify
            # that the JSON file exists.
            traceback.print_exc()
        output = os.path.join(tmpdir, 'output.json')
        if not os.path.exists(output):
            raise RuntimeError(f"Cannot find output file: {output}")
        with open(output) as f:
            data = json.load(f)

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
                pusher = push.Pusher(branch=repo.branch)
                pusher.run(data)
    session.close()


def main():
    db.connect()
    app.start(sys.argv[1:])


if __name__ == "__main__":
    main()
