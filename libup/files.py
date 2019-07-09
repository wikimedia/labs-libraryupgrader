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

from collections import OrderedDict
import json


class PackageJson:
    # TODO: Support non-dev deps
    def __init__(self, fname):
        self.fname = fname
        with open(fname, 'r') as f:
            self.data = json.load(f, object_pairs_hook=OrderedDict)

    def get_packages(self):
        return list(self.data['devDependencies'])

    def get_version(self, package):
        if package in self.data['devDependencies']:
            return self.data['devDependencies'][package]

        return None

    def set_version(self, package, version):
        if package in self.data['devDependencies']:
            self.data['devDependencies'][package] = version
            return

        raise RuntimeError('Unable to set version for %s to %s' % (package, version))

    def save(self):
        with open(self.fname, 'w') as f:
            out = json.dumps(self.data, indent='\t', ensure_ascii=False)
            f.write(out + '\n')


class ComposerJson:
    # TODO: Support non-dev deps
    def __init__(self, fname):
        self.fname = fname
        with open(fname, 'r') as f:
            self.data = json.load(f, object_pairs_hook=OrderedDict)

    def get_version(self, package):
        if package in self.data['require-dev']:
            return self.data['require-dev'][package]
        if 'extra' in self.data:
            suffix = package.split('/')[-1]
            if suffix in self.data['extra']:
                return self.data['extra'][suffix]

        return None

    def set_version(self, package, version):
        if package in self.data['require-dev']:
            self.data['require-dev'][package] = version
            return
        if 'extra' in self.data:
            suffix = package.split('/')[-1]
            if suffix in self.data['extra']:
                self.data['extra'][suffix] = version
                return

        raise RuntimeError('Unable to set version for %s to %s' % (package, version))

    def save(self):
        with open(self.fname, 'w') as f:
            out = json.dumps(self.data, indent='\t', ensure_ascii=False)
            f.write(out + '\n')
