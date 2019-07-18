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
import tempfile

from .collections import SaveDict


def test_savedict():
    def read(name):
        with open(name) as fr:
            return json.load(fr)

    with tempfile.NamedTemporaryFile(mode='w') as f:
        sdict = SaveDict({'test': True}, fname=f.name)
        assert read(f.name) == {'test': True}
        sdict['set'] = 'yes'
        assert read(f.name) == {'test': True, 'set': 'yes'}
        del sdict['test']
        assert read(f.name) == {'set': 'yes'}
