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
import requests

if os.path.exists('/srv/data'):
    DATA_ROOT = '/srv/data'
else:
    DATA_ROOT = os.path.abspath(os.path.join(
        os.path.dirname(os.path.dirname(__file__)), 'data'))
CACHE = os.path.join(DATA_ROOT, 'cache')
LOGS = os.path.join(DATA_ROOT, 'logs')
if os.path.exists('/srv/config'):
    # have a pre-existing /srv/config
    CONFIG_REPO = '/srv/config'
elif os.path.exists('/.dockerenv'):
    # FIXME: HACK HACK for inside docker because permissions are hard
    CONFIG_REPO = '/tmp/config'
else:
    CONFIG_REPO = os.path.join(DATA_ROOT, 'config')
RELEASES = os.path.join(CONFIG_REPO, 'releases.json')
MANAGERS = ['composer', 'npm']
TYPES = ['deps', 'dev']
CANARIES = [
    'mediawiki/extensions/Linter',
    'mediawiki/extensions/MassMessage',
    'mediawiki/extensions/VisualEditor',
    'mediawiki/skins/MonoBook',
    'oojs/ui',
]
GERRIT_USER = 'libraryupgrader'
GIT_NAME = 'libraryupgrader'
GIT_EMAIL = 'tools.libraryupgrader@tools.wmflabs.org'
PACKAGIST_MIRROR = 'https://repo.packagist.org'
SSH_AUTH_SOCK = '/tmp/ssh-agent.socket'
PHP_SECURITY_CHECK = 'https://php-security-checker.wmcloud.org/check_lock'


session = requests.Session()
