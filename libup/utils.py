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

import urllib.parse


def gerrit_url(repo: str, user=None, pw=None, ssh=False) -> str:
    host = ''
    if user:
        if pw:
            host = user + ':' + urllib.parse.quote_plus(pw) + '@'
        else:
            host = user + '@'

    host += 'gerrit.wikimedia.org'
    if ssh:
        return 'ssh://%s:29418/%s' % (host, repo)
    else:
        return 'https://%s/r/%s.git' % (host, repo)
