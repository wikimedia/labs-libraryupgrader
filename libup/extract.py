"""
Copyright (C) 2020 Kunal Mehta <legoktm@member.fsf.org>

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

import json
import os

from .model import Dependencies


def extract_dependencies(repo, branch):
    deps = []
    kwargs = {"repo": repo, "branch": branch}
    if os.path.exists('package.json'):
        with open('package.json') as f:
            pkg = json.load(f)
        for name, version in pkg.get('dependencies', {}).items():
            deps.append(Dependencies(
                name=name,
                version=version,
                mode="prod",
                **kwargs
            ))
        for name, version in pkg.get('devDependencies', {}).items():
            deps.append(Dependencies(
                name=name,
                version=version,
                mode="dev",
                **kwargs
            ))

    if os.path.exists('composer.json'):
        with open('composer.json') as f:
            pkg = json.load(f)
        for name, version in pkg.get('require', {}).items():
            deps.append(Dependencies(
                name=name,
                version=version,
                mode="prod",
                **kwargs
            ))
        for name, version in pkg.get('require-dev', {}).items():
            deps.append(Dependencies(
                name=name,
                version=version,
                mode="dev",
                **kwargs
            ))

    return deps
