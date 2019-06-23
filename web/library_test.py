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

import pytest

from library import Library


def test_sort():
    # Based on package name
    l1 = Library('foo', 'abcde', '0.1')
    l2 = Library('foo', 'edcba', '0.1')
    assert l1 < l2
    assert l2 > l1


def test_link():
    lib = Library('composer', 'test', '0.1')
    assert lib.link == 'https://packagist.org/packages/test'
    bad = Library('nope', 'test', '0.1')
    with pytest.raises(KeyError):
        z = bad.link  # noqa


# Integration tests (TODO: mock repository response):
def test_is_newer_composer():
    lib = Library('composer', 'mediawiki/mediawiki-codesniffer', '24.0.0')
    assert lib.is_newer() is True


def test_is_newer_npm():
    lib = Library('npm', 'grunt-banana-checker', '0.6.0')
    assert lib.is_newer() is True
