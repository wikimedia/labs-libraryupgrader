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

import json
import os

from . import DATA_ROOT


class Data:
    def __init__(self):
        self.current = os.path.join(DATA_ROOT, 'current')

    def find_files(self):
        for fname in os.listdir(self.current):
            if fname.endswith('.json'):
                yield os.path.join(self.current, fname)

    def get_data(self):
        data = {}
        for fname in self.find_files():
            with open(fname) as f:
                j = json.load(f)
            data[j['repo']] = j

        return data

    def get_repo_data(self, repo):
        expected = os.path.join(self.current, repo.replace('/', '_') + '.json')
        # Sanity check?
        if expected not in set(self.find_files()):
            raise ValueError("Didn't find %s" % repo)
        with open(expected) as f:
            return json.load(f)
