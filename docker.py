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

import subprocess
import time


CONCURRENT = 10
DOCKER_IMAGE = 'libraryupgrader'


def run(name: str, env: dict):
    """
    :param name: Name of container
    :param env: Environment values
    """
    args = ['docker', 'run', '--name=' + name]
    for key, value in env.items():
        args.extend(['--env', '%s=%s' % (key, value)])
    args.extend(['-d', DOCKER_IMAGE])
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
    out = subprocess.run(
        ['docker', 'logs', name],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )
    return out.stdout.decode()


def remove_container(name: str):
    subprocess.check_call(['docker', 'rm', name])
