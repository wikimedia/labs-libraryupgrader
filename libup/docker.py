#!/usr/bin/env python3
"""
Wrapper around the docker command
Copyright (C) 2017-2019 Kunal Mehta <legoktm@debian.org>

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

from . import CACHE

DOCKER_IMAGE = 'libraryupgrader'


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
        args.extend(['--env', f'{key}={value}'])
    if rm:
        args.append('--rm')
    if entrypoint is not None:
        args.extend(['--entrypoint', entrypoint])
    args.extend([
        '-v', CACHE + ':/cache',
    ])
    if mounts is not None:
        for outside, inside in mounts.items():
            args.extend(['-v', f'{outside}:{inside}'])
    if background:
        args.append('-d')
    args.append(DOCKER_IMAGE)
    if extra_args is not None:
        args.extend(extra_args)
    subprocess.check_call(args)
