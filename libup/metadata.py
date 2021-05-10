"""
Copyright (C) 2019 Kunal Mehta <legoktm@debian.org>

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
import semver
import semver.exceptions

from . import PACKAGIST_MIRROR, session


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