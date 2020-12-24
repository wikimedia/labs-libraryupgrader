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

from collections import OrderedDict
from contextlib import contextmanager
from datetime import datetime
import json
import os
import stat

from . import LOGS


@contextmanager
def cd(dirname):
    cwd = os.getcwd()
    os.chdir(dirname)
    try:
        yield dirname
    finally:
        os.chdir(cwd)


def gerrit_url(repo: str, user=None, ssh=False) -> str:
    if user is not None:
        prefix = user + '@'
    else:
        prefix = ''
    if ssh:
        return f'ssh://{prefix}gerrit.wikimedia.org:29418/{repo}'
    else:
        return f'https://{prefix}gerrit-replica.wikimedia.org/r/{repo}.git'


def load_ordered_json(fname) -> OrderedDict:
    with open(fname) as f:
        return json.load(f, object_pairs_hook=OrderedDict)


def save_pretty_json(data: dict, fname: str):
    with open(fname, 'w') as f:
        out = json.dumps(data, indent='\t', ensure_ascii=False)
        f.write(out + '\n')


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


def to_mw_time(dt: datetime) -> str:
    return dt.strftime('%Y%m%d%H%M%S')


def from_mw_time(mw: str) -> datetime:
    return datetime.strptime(mw, '%Y%m%d%H%M%S')
