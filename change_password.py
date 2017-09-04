#!/usr/bin/env python3
"""
Resets a Gerrit account's HTTP password
Copyright (C) 2017 Kunal Mehta <legoktm@member.fsf.org>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import json
import getpass
import requests
from requests.auth import HTTPDigestAuth
import sys

import gerrit
import upgrade

s = requests.Session()


def main():
    pw = getpass.getpass('HTTP Password for %s: ' % upgrade.GERRIT_USER)
    auth = HTTPDigestAuth('libraryupgrader', pw)
    # Check that we're logged in as the right user
    account = gerrit.make_request('GET', path='accounts/self', auth=auth)
    if account['username'] != upgrade.GERRIT_USER:
        print('Error, logged in as %(username)s (%(email)s)??' % account)
        sys.exit(1)
    print('Successfully logged in as %(username)s' % account)
    new_password = gerrit.make_request(
        'PUT',
        path='accounts/self/password.http',
        auth=auth,
        data=json.dumps({'generate': True}),
        headers={'Content-Type': 'application/json'}
    )
    print('The following is your new HTTP password, please save it:')
    print('----------')
    print(new_password)
    print('----------')


if __name__ == '__main__':
    main()
