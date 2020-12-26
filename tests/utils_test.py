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

import os

from libup import utils


def test_gerrit_url():
    assert utils.gerrit_url('repo/name') \
        == 'https://gerrit-replica.wikimedia.org/r/repo/name.git'
    assert utils.gerrit_url('repo/name', user='foo') \
        == 'https://foo@gerrit-replica.wikimedia.org/r/repo/name.git'
    assert utils.gerrit_url('repo/name', user='foo', ssh=True) \
        == 'ssh://foo@gerrit.wikimedia.org:29418/repo/name'
    assert utils.gerrit_url('repo/name', internal=True) \
        == 'file:///srv/git/repo-name.git'


def test_cd():
    cwd = os.getcwd()
    # Make sure the test will work
    assert '/' != cwd
    with utils.cd('/'):
        # We're now in the root dir
        assert '/' == os.getcwd()
    # And now we're back
    assert cwd == os.getcwd()


def test_mw_time():
    mw = '20201224070526'
    dt = utils.from_mw_time(mw)
    assert dt.year == 2020
    assert dt.month == 12
    assert dt.day == 24
    assert dt.hour == 7
    assert dt.minute == 5
    assert dt.second == 26
    assert utils.to_mw_time(dt) == mw
