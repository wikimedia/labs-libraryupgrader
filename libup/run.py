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
import wikimediaci_utils as ci_utils

from . import BRANCHES, config, db, gerrit, mw
from .model import Repository
from .tasks import run_check


def update_repositories(session):
    print('Updating list of repositories in database...')
    repositories = {}
    to_add = []
    for repo in session.query(Repository).all():
        repositories[repo.key()] = repo

    bundled = ci_utils.get_bundled_list()
    wm_deployed = ci_utils.get_wikimedia_deployed_list()
    canaries = config.repositories()['canaries']

    for repo in mw.get_everything():
        for branch in gerrit.repo_branches(repo):
            if branch not in BRANCHES:
                # We don't care about this one
                continue
            new = Repository(name=repo, branch=branch)
            try:
                # Exists, remove from list slated for deletion
                obj = repositories.pop(new.key())
            except KeyError:
                # Doesn't exist yet
                to_add.append(new)
                obj = new
            # Update bundled, etc. status
            obj.is_bundled = obj.name in bundled
            obj.is_wm_deployed = obj.name in wm_deployed
            obj.is_canary = obj.name in canaries

    session.add_all(to_add)
    for old in repositories.values():
        # should trigger cascading deletes in
        # advisories, dependencies, logs, etc.
        session.delete(old)
    session.commit()
    print('Done!')


def main():
    parser = argparse.ArgumentParser(description='Queue jobs to run')
    parser.add_argument('--limit', default=0, type=int, help='Limit')
    parser.add_argument('--fast', action='store_true', help='Skip some database updates')
    parser.add_argument('repo', nargs='?', help='Only queue this repository (optional)')
    args = parser.parse_args()

    db.connect()
    session = db.Session()
    if not args.fast:
        # Update the database first
        update_repositories(session)
        db.update_upstreams(session)

    count = 0
    if args.repo == 'none':
        gen = []
    elif args.repo == 'canaries':
        gen = session.query(Repository).filter_by(is_canary=True).all()
    elif args.repo == 'errors':
        gen = session.query(Repository).filter_by(is_error=True).all()
    elif args.repo == 'libraries':
        gen = session.query(Repository).filter(
            Repository.name.in_(list(mw.get_library_list()))
        ).all()
    elif args.repo:
        gen = session.query(Repository).filter_by(name=args.repo).all()
    else:
        gen = session.query(Repository).all()
    for repo in gen:
        print(f'Queuing {repo.name} ({repo.branch})')
        run_check.delay(repo.name, repo.branch)
        count += 1
        if args.limit and count >= args.limit:
            break


if __name__ == '__main__':
    main()
