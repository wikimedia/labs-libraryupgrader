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
import gzip
import json
import lzma
import os

from . import GIT_ROOT

# 2^16 per https://dev.mysql.com/doc/refman/8.0/en/storage-requirements.html
BLOB_SIZE = 65536


@contextmanager
def cd(dirname):
    cwd = os.getcwd()
    os.chdir(dirname)
    try:
        yield dirname
    finally:
        os.chdir(cwd)


def gerrit_url(repo: str, user=None, ssh=False, internal=False) -> str:
    if user is not None:
        prefix = user + '@'
    else:
        prefix = ''
    if ssh and internal:
        raise RuntimeError('Both ssh and internal cannot be True')
    if ssh:
        return f'ssh://{prefix}gerrit.wikimedia.org:29418/{repo}'
    elif internal:
        return f'file://{GIT_ROOT}/{repo.replace("/", "-")}.git'
    else:
        return f'https://{prefix}gerrit-replica.wikimedia.org/r/{repo}.git'


def load_ordered_json(fname) -> OrderedDict:
    with open(fname) as f:
        return json.load(f, object_pairs_hook=OrderedDict)


def save_pretty_json(data: dict, fname: str):
    with open(fname, 'w') as f:
        out = json.dumps(data, indent='\t', ensure_ascii=False)
        f.write(out + '\n')


def to_mw_time(dt: datetime) -> str:
    return dt.strftime('%Y%m%d%H%M%S')


def from_mw_time(mw: str) -> datetime:
    return datetime.strptime(mw, '%Y%m%d%H%M%S')


def maybe_compress(text: str) -> bytes:
    encoded = text.encode()
    if len(encoded) >= BLOB_SIZE:
        return b'l:' + lzma.compress(encoded)
    else:
        return encoded


def maybe_decompress(data: bytes) -> str:
    if data.startswith(b'l:'):
        return lzma.decompress(data[2:]).decode()
    elif data.startswith(b'g:'):
        return gzip.decompress(data[2:]).decode()
    else:
        return data.decode()
