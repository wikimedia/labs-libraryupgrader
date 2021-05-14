"""
Copyright (C) 2019 Kunal Mehta <legoktm@debian.org>

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
CONFIG_REPO = os.path.join(DATA_ROOT, 'config')
GIT_ROOT = '/srv/git'
MONITORING = os.path.join(CONFIG_REPO, 'monitoring.json')
RELEASES = os.path.join(CONFIG_REPO, 'releases.json')
REPOSITORIES = os.path.join(CONFIG_REPO, 'repositories.json')
MANAGERS = ['composer', 'npm']
GERRIT_USER = 'libraryupgrader'
GIT_NAME = 'libraryupgrader'
GIT_EMAIL = 'tools.libraryupgrader@tools.wmflabs.org'
PACKAGIST_MIRROR = 'https://repo.packagist.org'
SSH_AUTH_SOCK = '/tmp/ssh-agent.socket'
# TODO: pull this from somewhere else, like ExtensionDistributor
BRANCHES = ['main', 'REL1_36', 'REL1_35', 'REL1_31']
GIT_BRANCHES = ["master"] + BRANCHES


session = requests.Session()
