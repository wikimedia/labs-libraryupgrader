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
import semver


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

    def _metadata(self) -> dict:
        return {
            'composer': _get_composer_metadata,
            'npm': _get_npm_metadata,
        }[self.manager](self.name)

    def latest_version(self) -> str:
        return self._metadata()['latest']

    def description(self) -> str:
        return self._metadata()['description']

    def is_newer(self) -> bool:
        """if a newer version is available"""
        # Try and detect some operators to see if the current is a constraint
        # TODO: I don't think semver supports ^
        if any(True for x in '^><=|' if x in self.version):
            try:
                # Split on | since semver doesn't support that
                if any(
                        semver.match(self.latest_version(), part)
                        for part in self.version.split('|')
                ):
                    return True
            except ValueError:
                pass
            return False
        # Just do a safer/more basic semver comparison
        return LooseVersion(self.latest_version()) > LooseVersion(self.version)


# FIXME Don't use functools/lru_cache
@functools.lru_cache()
def _get_composer_metadata(package: str) -> dict:
    r = s.get('https://packagist.org/packages/%s.json' % package)
    resp = r.json()['package']
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
            if LooseVersion(normal) > LooseVersion(version):
                version = normal
        except ValueError:
            pass
    # print('Latest %s: %s' % (package, version))
    return {
        'latest': version,
        'description': resp['description'],
    }


@functools.lru_cache()
def _get_npm_metadata(package: str) -> dict:
    r = s.get('https://registry.npmjs.org/%s' % package)
    resp = r.json()
    # print('Latest %s: %s' % (package, version))
    return {
        'latest': resp['dist-tags']['latest'],
        'description': resp['description'],
    }
