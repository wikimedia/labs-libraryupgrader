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

from datetime import datetime
import os
import requests
import stat

if os.path.exists('/srv/data'):
    DATA_ROOT = '/srv/data'
else:
    DATA_ROOT = os.path.abspath(os.path.join(
        os.path.dirname(os.path.dirname(__file__)), 'data'))
LOGS = os.path.join(DATA_ROOT, 'logs')
if os.path.exists('/srv/config'):
    CONFIG_REPO = '/srv/config'
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
PACKAGIST_MIRROR = 'https://repo.packagist.org'
# TODO: this path is different inside the container
SSH_AUTH_SOCK = '/tmp/ssh-agent.socket'


session = requests.Session()


def date_log_dir():
    log_dir = os.path.join(LOGS, datetime.utcnow().strftime('%Y-%m-%d'))
    if not os.path.isdir(log_dir):
        os.mkdir(log_dir)
        os.chmod(
            log_dir,
            stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR |
            stat.S_IRGRP | stat.S_IWGRP | stat.S_IXGRP |
            stat.S_IROTH | stat.S_IWOTH | stat.S_IXOTH
        )
    return log_dir
