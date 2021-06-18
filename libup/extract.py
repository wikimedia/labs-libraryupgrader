"""
Copyright (C) 2020 Kunal Mehta <legoktm@debian.org>

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
import toml
from pathlib import Path

from .model import Dependency, Repository


def extract_dependencies(repo: Repository):
    deps = []
    kwargs = {"repo_id": repo.id}
    if os.path.exists('package.json'):
        with open('package.json') as f:
            pkg = json.load(f)
        for name, version in pkg.get('dependencies', {}).items():
            deps.append(Dependency(
                name=name,
                version=version,
                manager="npm",
                mode="prod",
                **kwargs
            ))
        for name, version in pkg.get('devDependencies', {}).items():
            deps.append(Dependency(
                name=name,
                version=version,
                manager="npm",
                mode="dev",
                **kwargs
            ))

    if os.path.exists('composer.json'):
        with open('composer.json') as f:
            pkg = json.load(f)
        for name, version in pkg.get('require', {}).items():
            deps.append(Dependency(
                name=name,
                version=version,
                manager="composer",
                mode="prod",
                **kwargs
            ))
        for name, version in pkg.get('require-dev', {}).items():
            deps.append(Dependency(
                name=name,
                version=version,
                manager="composer",
                mode="dev",
                **kwargs
            ))
    cargo_toml = Path("Cargo.toml")
    if cargo_toml.exists():
        pkg = toml.loads(cargo_toml.read_text())
        for name, info in pkg.get("dependencies", {}).items():
            deps.append(Dependency(
                name=name,
                version=determine_rust_version(info),
                manager="cargo",
                mode="prod",
                **kwargs
            ))
        for name, info in pkg.get("build-dependencies", {}).items():
            deps.append(Dependency(
                name=name,
                version=determine_rust_version(info),
                manager="cargo",
                # XXX: Should we differentiate between build deps and prod
                mode="prod",
                **kwargs
            ))
        for name, info in pkg.get("dev-dependencies", {}).items():
            deps.append(Dependency(
                name=name,
                version=determine_rust_version(info),
                manager="cargo",
                mode="dev",
                **kwargs
            ))

    return deps


def determine_rust_version(info) -> str:
    # Wow I wish I could write this in Rust instead
    if isinstance(info, str):
        return info
    if isinstance(info, dict):
        if "version" in info:
            return info["version"]
        elif "git" in info:
            version = info["git"]
            for key in ["branch", "rev"]:
                if key in info:
                    version += f"@{info[key]}"
            return version
    # TODO: Skip path deps?
    raise RuntimeError("Unable to determine version from: {}".format(json.dumps(info)))
