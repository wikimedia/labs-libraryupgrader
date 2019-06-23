#!/usr/bin/env python3
"""
Wrapper around the docker command
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

import os
import subprocess
import time

CONCURRENT = 6
DOCKER_IMAGE = 'libraryupgrader'
if os.path.exists('/srv/data'):
    DATA_ROOT = '/srv/data'
else:
    DATA_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), 'data'))


def run(name: str, env: dict, mounts=None, rm=False, entrypoint=None,
        extra_args=None, background=True):
    """
    :param name: Name of container
    :param env: Environment values
    :param entrypoint: Entrypoint to use
    :param extra_args: Args to pass onto the command
    :param background: Run in background or not
    """
    args = ['docker', 'run', '--name=' + name]
    for key, value in env.items():
        args.extend(['--env', '%s=%s' % (key, value)])
    if rm:
        args.append('--rm')
    if entrypoint is not None:
        args.extend(['--entrypoint', entrypoint])
    args.extend([
        '-v', DATA_ROOT + '/cache:/cache',
    ])
    if mounts is not None:
        for outside, inside in mounts.items():
            args.extend(['-v', '%s:%s' % (outside, inside)])
    if background:
        args.append('-d')
    args.append(DOCKER_IMAGE)
    if extra_args is not None:
        args.extend(extra_args)
    subprocess.check_call(args)


def get_running_containers() -> list:
    out = subprocess.check_output(['docker', 'ps', '-q']).decode().strip()
    if not out:
        return []
    return out.split('\n')


def wait_for_containers(count: int):
    while len(get_running_containers()) > count:
        print('Waiting...')
        time.sleep(2)


def logs(name: str) -> str:
    out = subprocess.check_output(
        ['docker', 'logs', name],
        stderr=subprocess.STDOUT
    )
    return out.decode()


def remove_container(name: str):
    subprocess.check_call(['docker', 'rm', name])
