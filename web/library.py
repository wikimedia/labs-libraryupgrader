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

from distutils.version import LooseVersion
import functools
import requests


s = requests.Session()


class Library:
    def __init__(self, manager: str, name: str, version: str):
        self.manager = manager
        self.name = name
        # TODO: should version be optional?
        self.version = version

    def __lt__(self, other):
        return self.name < other.name

    @property
    def link(self) -> str:
        return {
            'composer': 'https://packagist.org/packages/%s',
            'npm': 'https://www.npmjs.com/package/%s',
        }[self.manager] % self.name

    def latest_version(self) -> str:
        return {
            'composer': _get_composer_version,
            'npm': _get_npm_version,
        }[self.manager](self.name)

    def is_newer(self) -> bool:
        """if a newer version is available"""
        return LooseVersion(self.latest_version()) > LooseVersion(self.version)


@functools.lru_cache()
def _get_composer_version(package: str) -> str:
    r = s.get('https://packagist.org/packages/%s.json' % package)
    resp = r.json()['package']['versions']
    normalized = set()
    for ver in resp:
        if not ver.startswith('dev-') and not ver.endswith('-dev'):
            if ver.startswith('v'):
                normalized.add(ver[1:])
            else:
                normalized.add(ver)
    version = max(normalized)
    for normal in normalized:
        try:
            if LooseVersion(normal) > LooseVersion(version):
                version = normal
        except ValueError:
            pass
    # print('Latest %s: %s' % (package, version))
    return version


@functools.lru_cache()
def _get_npm_version(package: str) -> str:
    r = s.get('https://registry.npmjs.org/%s' % package)
    version = r.json()['dist-tags']['latest']
    # print('Latest %s: %s' % (package, version))
    return version
