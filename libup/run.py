#!/usr/bin/env python3
"""
Builds a dashboard for PHPCS runs
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

import argparse

from . import DATA_ROOT, date_log_dir
from . import mw
from .tasks import run_check


def main():
    parser = argparse.ArgumentParser(description='Queue jobs to run')
    parser.add_argument('--limit', default=0, type=int, help='Limit')
    parser.add_argument('repo', nargs='?', help='Only queue this repository (optional)')
    args = parser.parse_args()
    count = 0
    if args.repo:
        gen = [args.repo]
    else:
        gen = mw.get_everything()
    for repo in gen:
        print(repo)
        run_check.delay(repo, DATA_ROOT, date_log_dir())
        count += 1
        if args.limit and count >= args.limit:
            break


if __name__ == '__main__':
    main()
