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
import tempfile
import pytest


class Tempfs:
    def __init__(self):
        self.cwd = os.getcwd()
        self.tmpdir = tempfile.TemporaryDirectory()

    def create_file(self, filename, contents=''):
        """implement pyfakefs API"""
        dirname = os.path.dirname(filename)
        if dirname != '' and not os.path.exists(dirname):
            # Autocreate directory
            os.mkdir(dirname)
        with open(filename, 'w') as f:
            f.write(contents)

    def contents(self, filename):
        with open(filename) as f:
            return f.read()

    def json_contents(self, filename):
        return json.loads(self.contents(filename))

    def fixture(self, test, filename):
        return self.contents(os.path.join(
            os.path.dirname(__file__),
            'fixtures', test, filename
        ))

    def __enter__(self):
        os.chdir(self.tmpdir.name)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        os.chdir(self.cwd)
        self.tmpdir.cleanup()


@pytest.fixture()
def tempfs():
    with Tempfs() as fs:
        yield fs
