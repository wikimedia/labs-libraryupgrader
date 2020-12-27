"""
Copyright (C) 2020 Kunal Mehta <legoktm@member.fsf.org>

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
from typing import List, Dict, Optional

from . import config, db, session
from .model import Dependency


class Plan:
    """What's the update plan?"""
    def __init__(self, branch, pull=False):
        self.branch = branch
        self.canaries = config.repositories(pull=pull)['canaries']
        self.releases = config.releases(pull=pull).get(branch, {})

    def safe_version(self, manager: str, name: str) -> Optional[str]:
        try:
            return self.releases[manager][name]['to']
        except KeyError:
            return None

    def check(self, repo: str, deps: List[Dependency]) -> list:
        """return all the dependencies that need updating and the new version"""
        if repo in self.canaries:
            return self._check_canary(repo, deps)
        else:
            return self._check_regular(repo, deps)

    def status_canaries(self, dep: Dependency, expected) -> Dict[str, List[Dependency]]:
        """canaries that don't and do have this update"""
        session = db.Session()
        canaries = session.query(Dependency)\
            .filter_by(name=dep.name, manager=dep.manager, branch=self.branch)\
            .filter(Dependency.repo.in_(self.canaries))\
            .all()
        ret = {'missing': [], 'updated': []}
        for canary in canaries:
            if canary.version != expected:
                ret['missing'].append(canary.repo)
            else:
                ret['updated'].append(canary.repo)
        session.close()
        return ret

    def status_repositories(self, dep: Dependency, expected) -> Dict[str, List[Dependency]]:
        """repositories that don't have this update"""
        session = db.Session()
        repos = session.query(Dependency)\
            .filter_by(name=dep.name, manager=dep.manager, branch=self.branch)\
            .all()
        ret = {'missing': [], 'updated': []}
        for repo in repos:
            if repo.version != expected:
                ret['missing'].append(repo.repo)
            else:
                ret['updated'].append(repo.repo)
        session.close()
        return ret

    def _check_regular(self, repo: str, deps: List[Dependency]) -> list:
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
            status = self.status_canaries(dep, info['to'])
            if status['missing']:
                # Canaries aren't ready yet
                continue
            if dep.version != info['to']:
                updates.append((dep.manager, dep.name, info['to'], info['weight']))

        return updates

    def _check_canary(self, repo: str, deps: List[Dependency]) -> list:
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
            if dep.version != info['to']:
                updates.append((dep.manager, dep.name, info['to'], info['weight']))

        return updates

    def status(self):
        status = {}
        for manager, packages in self.releases.items():
            status[manager] = {}
            for name, info in packages.items():
                dep = Dependency(name=name, manager=manager)
                canaries = self.status_canaries(dep, info['to'])
                canaries_total = len(canaries['missing']) + len(canaries['updated'])
                if canaries_total > 0:
                    canaries_percent = int(100 * len(canaries['updated']) / canaries_total)
                else:
                    canaries_percent = 100
                repositories = self.status_repositories(dep, info['to'])
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


class HTTPPlan:
    """Class to get the update plan without directly hitting the db"""
    def __init__(self, branch):
        self.branch = branch

    def check(self, repo: str) -> list:
        # TODO: should we hit localhost instead?
        resp = session.post('https://libraryupgrader2.wmcloud.org/plan.json', params={
            'repository': repo,
            'branch': self.branch
        })
        resp.raise_for_status()
        data = resp.json()
        if data['status'] != 'ok':
            msg = data.get('error', 'An unknown error')
            raise RuntimeError(f"Error fetching plan: {msg}")
        return data['plan']
