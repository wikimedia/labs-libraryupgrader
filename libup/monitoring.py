"""
Copyright (C) 2021 Kunal Mehta <legoktm@debian.org>

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

import random

from . import session

GREETINGS = [
    "Hi!",
    "Howdy partner!",
    "Yooooooo.",
    "Guess what?!",
    "Dear maintainer,",
    "To whom it may concern:",
    "Ahoy there,",
    "Your attention is requested:",
]


def lookup(info: dict) -> str:
    if info['mode'] == 'release-monitoring':
        return release_monitoring(info['id'])
    else:
        raise RuntimeError(f"Invalid monitoring mode: {info['mode']}")


def release_monitoring(project_id: int) -> str:
    req = session.get("https://release-monitoring.org/api/v2/versions/", params={"project_id": project_id})
    req.raise_for_status()
    return req.json()["latest_version"]


def description(info: dict, latest_version: str, greeting=True) -> str:
    msg = f"A new upstream version of {info['name']} is now available: {latest_version}.\n"
    for url in info["urls"]:
        msg += "* {url}\n".format(url=url.format(version=latest_version))
    if greeting:
        msg = random.choice(GREETINGS) + "\n\n" + msg
    return msg
