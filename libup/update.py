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


class Update:
    """dataclass representing an update"""
    def __init__(self, manager, name, old, new, reason=''):
        self.manager = manager
        self.name = name
        self.old = old
        self.new = new
        self.reason = reason

    def to_dict(self):
        return {
            'manager': self.manager,
            'name': self.name,
            'old': self.old,
            'new': self.new,
            'reason': self.reason
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            data['manager'], data['name'], data['old'],
            data['new'], data['reason']
        )
