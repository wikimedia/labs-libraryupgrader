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

from collections import defaultdict
import json
import os
from typing import Dict, List

from . import DATA_ROOT, MANAGERS, TYPES
from .library import Library


class Data:
    def __init__(self):
        self.current = os.path.join(DATA_ROOT, 'current')

    def find_files(self):
        for fname in os.listdir(self.current):
            if fname.endswith('.json'):
                yield os.path.join(self.current, fname)

    def get_data(self) -> dict:
        data = {}
        for fname in self.find_files():
            with open(fname) as f:
                j = json.load(f)
            data[j['repo']] = j

        return data

    def get_repo_data(self, repo) -> dict:
        expected = os.path.join(self.current, repo.replace('/', '_') + '.json')
        # Sanity check?
        if expected not in set(self.find_files()):
            raise ValueError("Didn't find %s" % repo)
        with open(expected) as f:
            return json.load(f)

    def get_deps(self, info) -> Dict[str, Dict[str, List[Library]]]:
        deps = defaultdict(lambda: defaultdict(list))  # type: Dict[str, Dict[str, List[Library]]]
        for manager in MANAGERS:
            if info['%s-deps' % manager]:
                minfo = info['%s-deps' % manager]
                for type_ in TYPES:
                    if minfo[type_]:
                        for name, version in minfo[type_].items():
                            deps[manager][type_].append(Library(manager, name, version))

        return deps
