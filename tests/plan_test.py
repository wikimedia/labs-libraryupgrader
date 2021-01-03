"""
Copyright (C) 2020 Kunal Mehta <legoktm@member.fsf.org>

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

import pytest

from libup import plan


@pytest.mark.parametrize('current,wanted,expected', (
    # String equals
    ('0.5.0', '0.5.0', True),
    # String not equals
    ('0.5.0', '0.6.0', False),
    # Same but semver ^
    ('^1.0.0', '1.0.0', True),
    # Semver compatible, but not the same
    ('^1.0.0', '1.1.0', False),
    # We want a semver expression which is compatible
    ('1.0.0', '^1 || ^2', False),
    # Current is newer than what we want, good enough
    ('0.6.0', '0.5.0', True),
    # semver greater, but not string greater
    ('0.10.0', '0.9.0', True),
    # special npm syntax
    ('file:tests/foo', '1.0.0', True),
))
def test_equals(current, wanted, expected):
    actual = plan.equals(current, wanted)
    assert actual == expected
