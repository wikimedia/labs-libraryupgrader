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

import re
import semver
import semver.exceptions
import traceback


def is_greater_than(first, second) -> bool:
    try:
        """if second > first"""
        # Try and detect some operators to see if the current is a multi-constraint
        if re.search(r'[|,]', first):
            constraint = semver.parse_constraint(first)
            return constraint.allows(semver.Version.parse(second))

        # Remove some constraint stuff because we just want versions
        first = re.sub(r'[\^~><=]', '', first)
        return semver.Version.parse(second) > semver.Version.parse(first)
    except semver.exceptions.ParseVersionError:
        traceback.print_exc()
        return False


def is_greater_than_or_equal_to(first: str, second: str) -> bool:
    """if second >= first"""
    # Try and detect some operators to see if the current is a multi-constraint
    if re.search(r'[|,]', first):
        constraint = semver.parse_constraint(first)
        return constraint.allows(semver.Version.parse(second))

    # Remove some constraint stuff because we just want versions
    second = re.sub(r'[\^~><=]', '', second)

    return semver.Version.parse(second) >= semver.Version.parse(first)
