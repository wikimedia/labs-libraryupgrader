"""
Copyright (C) 2021 Kunal Mehta <legoktm@debian.org>

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

from libup import metadata


@pytest.mark.skip(reason="broken")
def test_composer_metadata():
    # Dead package, won't be updated again
    data = metadata.get_composer_metadata("mediawiki/core")
    assert data["latest"] == "1.37.1"
    assert data["description"].startswith("Free software wiki application")
    # Verify this doesn't throw an exception (it used to)
    metadata.get_composer_metadata("roave/security-advisories")


def test_cargo_metadata():
    data = metadata.get_cargo_metadata("parsoid")
    assert "Parsoid" in data["description"]
