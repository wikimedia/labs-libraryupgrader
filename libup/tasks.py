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
import json
import os
import random
import string
import subprocess
import tempfile
import traceback

from . import DATA_ROOT, db, docker, push, utils, ssh
from .extract import extract_dependencies

app = Celery('tasks', broker='amqp://localhost')


def _random_string():
    return ''.join(random.choice(string.ascii_letters) for _ in range(15))


@app.task
def run_check(repo: str, data_root: str, log_dir: str):
    rand = _random_string()
    with tempfile.TemporaryDirectory() as tmpdir:
        with utils.cd(tmpdir):
            # TODO: Move this logic out of pusher?
            pusher = push.Pusher()
            pusher.clone(repo)
            deps = extract_dependencies(repo, "master")
            db.update_dependencies(repo, "master", deps)
            # FIXME: don't throw this clone away

    try:
        docker.run(
            name=rand,
            env={},
            background=False,
            mounts={
                log_dir: '/out',
                DATA_ROOT: '/srv/data:ro',
            },
            rm=True,
            extra_args=['libup-ng', repo, '/out/%s.json' % rand],
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
        fname = os.path.join(data_root, 'current', repo.replace('/', '_') + '.json')
        with open(fname, 'w') as fw:
            text = fr.read()
            fw.write(text)
    data = json.loads(text)
    log_url_path = output.replace(f'{data_root}/', '').replace('.json', '')
    data['message'] = f'View logs for this commit at ' \
                      f'https://libraryupgrader2.wmcloud.org/{log_url_path}'
    if data.get('push') and ssh.is_key_loaded():
        with tempfile.TemporaryDirectory() as tmpdir:
            with utils.cd(tmpdir):
                pusher = push.Pusher()
                pusher.run(data)
