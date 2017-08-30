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

import functools
import os
import requests
import semver
import shutil
import subprocess
import tempfile

CODESNIFFER = 'mediawiki/mediawiki-codesniffer'
GERRIT_URL = 'https://gerrit.wikimedia.org/r/mediawiki/extensions/%s.git'

s = requests.Session()


@functools.lru_cache()
def get_packagist_version(package):
    r = s.get('https://packagist.org/packages/%s.json?1' % package)
    resp = r.json()['package']['versions']
    normalized = set()
    for ver in resp:
        if not (ver.startswith('dev-') or ver.endswith('-dev')):
            if ver.startswith('v'):
                normalized.add(ver[1:])
            else:
                normalized.add(ver)
    print(normalized)
    version = max(normalized)
    for normal in normalized:
        try:
            if semver.compare(version, normal) == -1:
                version = normal
        except ValueError:
            pass
    print('Latest %s: %s' % (package, version))
    return version


def commit_and_push(files, msg, branch, topic, plus2=False, push=True):
    f = tempfile.NamedTemporaryFile(delete=False)
    f.write(bytes(msg, 'utf-8'))
    f.close()
    subprocess.check_call(['git', 'add'] + files)
    subprocess.check_call(['git', 'commit', '-F', f.name])
    per = '%topic={0}'.format(topic)
    if plus2:
        per += ',l=Code-Review+2'
    push_cmd = ['git', 'push', 'origin',
                'HEAD:refs/for/{0}'.format(branch) + per]
    if push:
        subprocess.check_call(push_cmd)
    else:
        print(' '.join(push_cmd))
    os.unlink(f.name)


def test():
    ext = os.environ['EXT']
    subprocess.check_call(['git', 'clone', GERRIT_URL % ext, '--depth=1'])
    os.chdir(ext)
    version = os.environ.get('VERSION')
    if version:
        # Also runs composer install
        subprocess.check_call(['composer', 'require', CODESNIFFER, version, '--prefer-dist', '--dev'])
    else:
        subprocess.check_call(['composer', 'install'])
    shutil.copy('/usr/src/myapp/phpcs.xml.sample', 'phpcs.xml')
    print('------------')
    # Don't use check_call since we expect this to fail
    out = subprocess.run(['vendor/bin/phpcs', '--report=json'], stdout=subprocess.PIPE)
    print(out.stdout.decode())
    print('------------')


def main():
    mode = os.environ['MODE']
    if mode == 'test':
        test()
    else:
        raise ValueError('Unknown mode: ' + mode)


if __name__ == '__main__':
    main()
