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

from libup.model import Log, BLOB_SIZE


def test_log():
    log = Log()
    log.set_text('foobarbaz')
    assert log.get_text() == 'foobarbaz'
    large_text = 'AAAA' * 999999
    assert len(large_text) > BLOB_SIZE
    log.set_text(large_text)
    # internal encoding detail
    assert log.text.startswith(b'g:')
    assert log.get_text() == large_text
