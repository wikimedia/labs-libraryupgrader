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

from . import PACKAGIST_MIRROR, session


def get_composer_metadata(package: str) -> dict:
    if package == 'php' or package.startswith('ext-'):
        # These aren't real composer packages
        return {
            'latest': '0.0.0',
            'description': 'Unknown package',
        }
    r = session.get(f'{PACKAGIST_MIRROR}/p2/{package}.json')
    if not r.ok:
        return {
            'latest': '0.0.0',
            'description': f'Unknown package (HTTP {r.status_code})'
        }
    try:
        resp = r.json()['packages'][package]
    except (KeyError, json.decoder.JSONDecodeError):
        return {
            'latest': '0.0.0',
            'description': 'Unknown package',
        }
    version = resp[0]["version"]
    # Potentially strip v prefix
    if version.startswith("v"):
        version = version[1:]
    parts = version.split('.')
    if len(parts) == 2:
        # see T242276
        version += '.0'
    # print('Latest %s: %s' % (package, version))
    return {
        'latest': version,
        'description': resp[0]['description'],
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


def get_cargo_metadata(package: str) -> dict:
    r = session.get(f"https://crates.io/api/v1/crates/{package}")
    resp = r.json()["crate"]
    # Get highest stable version if available, otherwise get highest version
    # regardless of alpha/rc/etc. status
    version = resp.get("max_stable_version")
    if version is None:
        version = resp["max_version"]
    return {
        "latest": version,
        "description": resp["description"]
    }


def get_metadata(manager: str, name: str) -> dict:
    if manager == "composer":
        return get_composer_metadata(name)
    elif manager == "npm":
        return get_npm_metadata(name)
    elif manager == "cargo":
        return get_cargo_metadata(name)
    else:
        raise RuntimeError(f"Unknown manager: {manager}")
