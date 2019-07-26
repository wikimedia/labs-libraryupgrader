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
import traceback

from . import CONFIG_REPO, DATA_ROOT, docker

app = Celery('tasks', broker='amqp://localhost')


def _random_string():
    return ''.join(random.choice(string.ascii_letters) for _ in range(15))


@app.task
def run_check(repo: str, data_root: str, log_dir: str):
    rand = _random_string()
    try:
        docker.run(
            name=rand,
            env={},
            background=False,
            mounts={
                log_dir: '/out',
                DATA_ROOT: '/srv/data:ro',
                CONFIG_REPO: '/srv/config'
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
    # Copy it over to the current directory,
    # potentially overwriting existing results
    with open(output) as fr:
        fname = os.path.join(data_root, 'current', repo.replace('/', '_') + '.json')
        with open(fname, 'w') as fw:
            text = fr.read()
            fw.write(text)
    data = json.loads(text)
    # TODO: How is the ssh-agent going to even make it to this process??
    if False and data['push'] and 'SSH_AUTH_SOCK' in os.environ:
        rand2 = _random_string()
        docker.run(
            name=rand2,
            env={'SSH_AUTH_SOCK': '/ssh-agent'},
            background=False,
            mounts={log_dir: '/out', os.environ['SSH_AUTH_SOCK']: '/ssh-agent'},
            rm=True,
            extra_args=['libup-push', '/out/%s.json' % rand],
        )
