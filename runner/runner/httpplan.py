"""
Copyright (C) 2020 Kunal Mehta <legoktm@debian.org>

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

import requests


class HTTPPlan:
    """Class to get the update plan without directly hitting the db"""
    def __init__(self, branch):
        self.branch = branch

    def check(self, repo: str) -> list:
        # Retry this up to 5 times
        for _ in range(5):
            resp = requests.post(
                'https://libraryupgrader2.wmcloud.org/plan.json',
                params={
                    'repository': repo,
                    'branch': self.branch
                }
            )
            if resp.ok:
                # If it's OK, short-circuit
                break
        # If the last request was an error, raise it
        resp.raise_for_status()
        data = resp.json()
        if data['status'] != 'ok':
            msg = data.get('error', 'An unknown error')
            raise RuntimeError(f"Error fetching plan: {msg}")
        return data['plan']
