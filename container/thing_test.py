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

import thing


def test_gerrit_url():
    assert thing.gerrit_url('repo/name') \
        == 'https://gerrit.wikimedia.org/r/repo/name.git'
    assert thing.gerrit_url('repo/name', user='foo') \
        == 'https://foo@gerrit.wikimedia.org/r/repo/name.git'
    assert thing.gerrit_url('repo/name', user='foo', pw='bar!!+/') \
        == 'https://foo:bar%21%21%2B%2F@gerrit.wikimedia.org/r/repo/name.git'


def test_update_coc(fs):
    # No CoC.md
    assert thing.update_coc() == ''
    # Already correct CoC.md
    fs.create_file('CODE_OF_CONDUCT.md',
                   contents='The development of this software is covered by a [Code of Conduct]'
                            '(https://www.mediawiki.org/wiki/Special:MyLanguage/Code_of_Conduct).\n')
    assert thing.update_coc() == ''


def test_actually_update_coc(fs):
    # The wrong CoC.md
    fs.create_file('CODE_OF_CONDUCT.md',
                   contents='The development of this software is covered by a [Code of Conduct]'
                            '(https://www.mediawiki.org/wiki/Code_of_Conduct).\n')
    assert thing.update_coc() == 'And updating CoC link to use Special:MyLanguage (T202047).\n'
