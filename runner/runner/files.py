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

from collections import OrderedDict
import json
from typing import Optional


def load_ordered_json(fname) -> OrderedDict:
    with open(fname) as f:
        return json.load(f, object_pairs_hook=OrderedDict)


def save_pretty_json(data: dict, fname: str):
    with open(fname, 'w') as f:
        out = json.dumps(data, indent='\t', ensure_ascii=False)
        f.write(out + '\n')


class PackageJson:
    # TODO: Support non-dev deps
    def __init__(self, fname):
        self.fname = fname
        self.data = load_ordered_json(self.fname)

    def get_packages(self):
        return list(self.data.get('devDependencies', {}))

    def get_version(self, package: str) -> Optional[str]:
        try:
            return self.data['devDependencies'][package]
        except KeyError:
            return None

    def set_version(self, package: str, version: str):
        if package in self.data.get('devDependencies', {}):
            self.data['devDependencies'][package] = version
            return

        raise RuntimeError(f'Unable to set version for {package} to {version}')

    def remove_package(self, package):
        if 'devDependencies' in self.data:
            del self.data['devDependencies'][package]
            return

        raise RuntimeError(f'Unable to remove {package}')

    def save(self):
        save_pretty_json(self.data, self.fname)


class PackageLockJson:
    def __init__(self, fname='package-lock.json'):
        self.fname = fname
        self.data = load_ordered_json(self.fname)
        if self.data["lockfileVersion"] > 2:
            # TODO: support lockfileVersion 3
            raise RuntimeError("lockfileVersion > 2 is not supported")

    def get_version(self, package: str) -> Optional[str]:
        try:
            return self.data['dependencies'][package]['version']
        except KeyError:
            return None

    def set_version(self, package: str, version: str):
        raise NotImplementedError

    def save(self):
        # For rollbacks and stuff. We don't allow modification though.
        save_pretty_json(self.data, self.fname)


class ComposerJson:
    # TODO: Support non-dev deps
    def __init__(self, fname):
        self.fname = fname
        self.data = load_ordered_json(self.fname)

    def get_version(self, package: str) -> Optional[str]:
        if package in self.data.get('require-dev', {}):
            return self.data['require-dev'][package]
        if 'extra' in self.data:
            suffix = package.split('/')[-1]
            if suffix in self.data['extra']:
                return self.data['extra'][suffix]

        return None

    def get_extra(self, extra):
        if 'extra' in self.data:
            if extra in self.data['extra']:
                return self.data['extra'][extra]

        return None

    def set_version(self, package, version):
        if package in self.data.get('require-dev', {}):
            self.data['require-dev'][package] = version
            return
        if 'extra' in self.data:
            suffix = package.split('/')[-1]
            if suffix in self.data['extra']:
                self.data['extra'][suffix] = version
                return

        raise RuntimeError(f'Unable to set version for {package} to {version}')

    def add_package(self, package: str, version: str):
        if 'require-dev' not in self.data:
            self.data['require-dev'] = {}

        self.data['require-dev'][package] = version

    def remove_package(self, package):
        if package in self.data.get('require-dev', {}):
            del self.data['require-dev'][package]
            return

        raise RuntimeError(f'Unable to remove {package}')

    def remove_extra(self, extra):
        if 'extra' in self.data:
            if extra in self.data['extra']:
                del self.data['extra'][extra]
                if len(self.data['extra']) == 0:
                    del self.data['extra']
                return

        raise RuntimeError(f'Unable to remove {extra}')

    def save(self):
        if 'require-dev' in self.data:
            # Re-sort dependencies by package name
            self.data['require-dev'] = OrderedDict(sorted(self.data['require-dev'].items(), key=lambda x: x[0]))
        save_pretty_json(self.data, self.fname)
