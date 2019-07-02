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

import wikimediaci_utils as ci

from . import DATA_ROOT, date_log_dir
from .tasks import run_check


def main():
    for repo in sorted(ci.mw_things_repos()):
        print(repo)
        run_check.delay(repo, DATA_ROOT, date_log_dir())


if __name__ == '__main__':
    main()
