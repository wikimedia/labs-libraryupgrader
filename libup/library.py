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

import functools
import json
import re
import semver
import semver.exceptions
import traceback

from . import PACKAGIST_MIRROR, session
from .plan import Plan


class Library:
    def __init__(self, manager: str, name: str, version: str):
        self.manager = manager
        self.name = name
        self.version = version

    def __lt__(self, other):
        return self.name < other.name

    def _metadata(self) -> dict:
        return get_metadata(self.manager, self.name)

    def latest_version(self) -> str:
        return self._metadata()['latest']

    def get_latest(self):
        return Library(
            self.manager, self.name,
            self.latest_version()
        )

    def is_safe_upgrade(self, version) -> bool:
        """whether the specified version is a good release"""
        plan = Plan('master')
        safe = plan.safe_version(self.manager, self.name)
        if safe is None:
            return False
        return version == safe

    def is_latest_safe(self) -> bool:
        """is the latest version a good release"""
        # HACK HACK HACK
        if self.name == 'mediawiki/mediawiki-codesniffer' \
                and (self.version.startswith('19.') or self.version.startswith('26.')):
            # Don't upgrade codesniffer 19.x as it is the last version with php5 support (T228186)
            # Don't upgrade codesniffer 26.x as it is the last version with php7 support
            return False
        return self.is_safe_upgrade(self.latest_version())

    def is_newer(self) -> bool:
        if self.version.strip() in ['*', 'latest']:
            # special case, T243262
            return False
        elif self.version.startswith('git'):
            # see T268254#6670861
            return False
        return is_greater_than(self.version, self.latest_version())


def is_greater_than(first, second) -> bool:
    try:
        """if second > first"""
        # Try and detect some operators to see if the current is a multi-constraint
        if re.search(r'[|,]', first):
            constraint = semver.parse_constraint(first)
            return constraint.allows(semver.Version.parse(second))

        # Remove some constraint stuff because we just want versions
        first = re.sub(r'[\^~><=]', '', first)
        return semver.Version.parse(second) > semver.Version.parse(first)
    except semver.exceptions.ParseVersionError:
        traceback.print_exc()
        return False


def is_greater_than_or_equal_to(first, second) -> bool:
    """if second >= first"""
    # Try and detect some operators to see if the current is a multi-constraint
    if re.search(r'[|,]', first):
        constraint = semver.parse_constraint(first)
        return constraint.allows(semver.Version.parse(second))

    # Remove some constraint stuff because we just want versions
    first = re.sub(r'[\^~><=]', '', first)

    return semver.Version.parse(second) >= semver.Version.parse(first)


# FIXME Don't use functools/lru_cache
@functools.lru_cache()
def get_composer_metadata(package: str) -> dict:
    if package == 'php' or package.startswith('ext-'):
        # These aren't real composer packages
        return {
            'latest': '0.0.0',
            'description': 'Unknown package',
        }
    r = session.get(f'{PACKAGIST_MIRROR}/packages/{package}.json')
    try:
        resp = r.json()['package']
    except (KeyError, json.decoder.JSONDecodeError):
        return {
            'latest': '0.0.0',
            'description': 'Unknown package',
        }
    normalized = set()
    for ver in resp['versions']:
        if not ver.startswith('dev-') and not ver.endswith('-dev'):
            if ver.startswith('v'):
                normalized.add(ver[1:])
            else:
                normalized.add(ver)
    version = max(normalized)
    for normal in normalized:
        try:
            if semver.Version.parse(normal) > semver.Version.parse(version):
                version = normal
        except semver.exceptions.ParseVersionError:
            # TODO: log these exceptions
            pass
    parts = version.split('.')
    if len(parts) == 2:
        # see T242276
        version += '.0'
    # print('Latest %s: %s' % (package, version))
    return {
        'latest': version,
        'description': resp['description'],
    }


@functools.lru_cache()
def get_npm_metadata(package: str) -> dict:
    r = session.get('https://registry.npmjs.org/%s' % package)
    resp = r.json()
    # print('Latest %s: %s' % (package, version))
    try:
        latest = resp['dist-tags']['latest']
        description = resp['description']
    except KeyError:
        latest = '0.0.0'
        description = 'Unknown package'
    return {
        'latest': latest,
        'description': description,
    }


def get_metadata(manager: str, name: str) -> dict:
    if manager == "composer":
        return get_composer_metadata(name)
    elif manager == "npm":
        return get_npm_metadata(name)
    else:
        raise RuntimeError(f"Unknown manager: {manager}")
