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

import json
import os
import subprocess

from . import CONFIG_REPO, RELEASES


def config(pull=False) -> dict:
    if not os.path.exists(RELEASES):
        subprocess.check_call([
            'git', 'clone',
            'https://gerrit.wikimedia.org/r/labs/libraryupgrader/config',
            CONFIG_REPO
        ], cwd=os.path.dirname(CONFIG_REPO))
    elif pull:
        subprocess.check_call(['git', 'pull'], cwd=CONFIG_REPO)

    with open(RELEASES) as f:
        return json.load(f)


def should_push(pull=True) -> bool:
    """whether to push changes"""
    return config(pull=pull)['push']
