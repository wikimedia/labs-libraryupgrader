#!/usr/bin/env python3
"""
Common functions for MediaWiki stuff things.
Copyright (C) 2017-2018, 2020 Kunal Mehta <legoktm@member.fsf.org>

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

import itertools
import wikimediaci_utils as ci

from . import config, gerrit


def get_everything():
    ignored = config.repositories(pull=True).get('ignore', [])
    yield from itertools.filterfalse(
        # Must fail this test to be returned
        lambda x: x in ignored,
        itertools.chain(
            sorted(ci.mw_things_repos()),
            sorted(get_library_list())
        )
    )


def get_library_list():
    """Get the list of repositories from the config repo"""
    repos = config.repositories()['repositories']
    for repo in repos:
        if repo.endswith('/*'):
            # Strip the * before searching for the prefix
            for found in gerrit.list_projects(repo[:-1]):
                # Ignore deploy repositories
                if not found.endswith(('/deploy', '-deploy')):
                    yield found
        else:
            yield repo
