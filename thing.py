#!/usr/bin/env python3
"""
Automatically updates library dependencies
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

# == NOTE ==
# This script runs *inside* a Docker container

import os
import shutil
import subprocess

CODESNIFFER = 'mediawiki/mediawiki-codesniffer'
GERRIT_URL = 'https://gerrit.wikimedia.org/r/mediawiki/extensions/%s.git'


def main():
    ext = os.environ['EXT']
    subprocess.check_call(['git', 'clone', GERRIT_URL % ext, '--depth=1'])
    os.chdir(ext)
    subprocess.check_call(['composer', 'update'])
    version = os.environ.get('VERSION')
    if version:
        subprocess.check_call(['composer', 'require', CODESNIFFER, version, '--prefer-dist'])
    shutil.copy('/usr/src/myapp/phpcs.xml.sample', 'phpcs.xml')
    print('------------')
    # Don't use check_call since we expect this to fail
    out = subprocess.run(['vendor/bin/phpcs', '--report=json'], stdout=subprocess.PIPE)
    print(out.stdout.decode())
    print('------------')


if __name__ == '__main__':
    main()
