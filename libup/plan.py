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

import re
import semver
import semver.exceptions
from sqlalchemy.orm import joinedload
from typing import List, Dict, Optional

from . import config
from .model import Dependency, Repository


class Plan:
    """What's the update plan?"""
    def __init__(self, branch, pull=False):
        self.branch = branch
        self.canaries = config.repositories(pull=pull)['canaries']
        # Don't bother pulling for this, we just did above
        self.releases = config.releases(pull=False).get(branch, {})

    def safe_version(self, manager: str, name: str) -> Optional[str]:
        try:
            return self.releases[manager][name]['to']
        except KeyError:
            return None

    def check(self, session, repo: str, deps: List[Dependency]) -> list:
        """return all the dependencies that need updating and the new version"""
        if repo in self.canaries:
            return self._check_canary(deps)
        else:
            return self._check_regular(session, deps)

    def status_canaries(self, session, dep: Dependency, expected) -> Dict[str, List[Repository]]:
        """canaries that don't and do have this update"""
        canaries = session.query(Dependency).join(Repository)\
            .filter(Dependency.name == dep.name, Dependency.manager == dep.manager,
                    Repository.name.in_(self.canaries), Repository.branch == self.branch)\
            .options(joinedload(Dependency.repository))\
            .all()
        ret: Dict[str, List[Repository]] = {'missing': [], 'updated': []}
        for canary in canaries:
            if not equals(canary.version, expected):
                ret['missing'].append(canary.repository)
            else:
                ret['updated'].append(canary.repository)
        session.close()
        return ret

    def status_repositories(self, session, dep: Dependency, expected) -> Dict[str, List[Repository]]:
        """repositories that don't have this update"""
        repos = session.query(Dependency).join(Repository)\
            .filter(Dependency.name == dep.name, Dependency.manager == dep.manager,
                    Repository.branch == self.branch)\
            .options(joinedload(Dependency.repository))\
            .all()
        ret: Dict[str, List[Repository]] = {'missing': [], 'updated': []}
        for repo in repos:
            if not equals(repo.version, expected):
                ret['missing'].append(repo.repository)
            else:
                ret['updated'].append(repo.repository)
        session.close()
        return ret

    def _check_regular(self, session, deps: List[Dependency]) -> list:
        updates = []
        for dep in deps:
            try:
                info = self.releases[dep.manager][dep.name]
            except KeyError:
                # We're not tracking this dependency
                continue
            if 'skip' in info and dep.version.startswith(tuple(info['skip'])):
                # To be skipped
                continue
            status = self.status_canaries(session, dep, info['to'])
            if status['missing']:
                # Canaries aren't ready yet
                continue
            if not equals(dep.version, info['to']):
                updates.append((dep.manager, dep.name, info['to'], info['weight']))

        return updates

    def _check_canary(self, deps: List[Dependency]) -> list:
        updates = []
        for dep in deps:
            try:
                info = self.releases[dep.manager][dep.name]
            except KeyError:
                # We're not tracking this dependency
                continue
            if 'skip' in info and dep.version.startswith(tuple(info['skip'])):
                # To be skipped
                continue
            if not equals(dep.version, info['to']):
                updates.append((dep.manager, dep.name, info['to'], info['weight']))

        return updates

    def status(self, session):
        status = {}
        for manager, packages in self.releases.items():
            status[manager] = {}
            for name, info in packages.items():
                dep = Dependency(name=name, manager=manager)
                canaries = self.status_canaries(session, dep, info['to'])
                canaries_total = len(canaries['missing']) + len(canaries['updated'])
                if canaries_total > 0:
                    canaries_percent = int(100 * len(canaries['updated']) / canaries_total)
                else:
                    canaries_percent = 100
                repositories = self.status_repositories(session, dep, info['to'])
                repositories_total = len(repositories['missing']) + len(repositories['updated'])
                if repositories_total > 0:
                    repositories_percent = int(100 * len(repositories['updated']) / repositories_total)
                else:
                    repositories_percent = 100
                status[manager][name] = {
                    'info': info,
                    'stats': {
                        'canaries': {
                            'total': canaries_total,
                            'percent': canaries_percent
                        },
                        'repositories': {
                            'total': repositories_total,
                            'percent': repositories_percent
                        }
                    },
                    'canaries': canaries,
                    'repositories': repositories
                }

        return status


def equals(current, wanted):
    """
    for the purpose of deciding whether want to upgrade, is the
    current version OK enough or do we need to intervene?
    """
    if current == wanted:
        return True
    if current.startswith('file:'):
        # Special npm syntax (see wdio-mediawiki in mediawiki/core)
        return True
    try:
        # Remove some constraint stuff because we just want versions
        first = re.sub(r'[\^~><=]', '', current)
        if semver.Version.parse(first) >= semver.Version.parse(wanted):
            return True
    except semver.exceptions.ParseVersionError:
        pass

    return False
