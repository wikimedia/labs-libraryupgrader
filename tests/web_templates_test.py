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

import jinja2
from pathlib import Path
import pytest


TEMPLATES = (Path(__file__).absolute().parent.parent / 'libup/web/templates').glob('*.html')


@pytest.mark.parametrize('path', TEMPLATES)
def test_templates(path):
    """verify templates have correct jinja2 syntax"""
    with path.open() as f:
        contents = f.read()
    try:
        jinja2.Template(contents)
    except TypeError:
        # TypeError is expected, we let SyntaxErrors bubble up
        pass
