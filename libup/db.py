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

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from . import config, metadata
from .model import Dependency, Dependencies, Repository, Upstream


Session = sessionmaker()


def sql_uri() -> str:
    # Keep in sync with alembic.ini (TODO: is there a better way to do this?)
    try:
        return config.private()["mariadb_connection"]
    except KeyError:
        return "mysql+pymysql://libup:password@localhost/libup?charset=utf8mb4"


def connect():
    engine = create_engine(sql_uri(), pool_pre_ping=True, pool_recycle=300)
    Session.configure(bind=engine)
    return engine


def update_dependencies(session, repo: Repository, deps):
    if not deps:
        return

    to_delete = []

    existing = Dependencies(repo.dependencies)
    for dep in deps:
        found = existing.pop(dep)
        if not found:
            repo.dependencies.append(dep)
            continue
        if found.same_version(dep):
            # Nothing to do
            continue
        else:
            # session automatically tracks dirty objects
            found.version = dep.version
            continue

    # Delete all the remaining existing that wasn't popped
    to_delete.extend(existing.all())

    # TODO: bulk operations?
    for delete in to_delete:
        session.delete(delete)

    session.commit()


def update_upstreams(session):
    print('Fetching upstream metadata for packages...')
    deps = session.query(Dependency).all()
    libs = set()
    for dep in deps:
        # TODO: do this unique filtering in SQL
        libs.add((dep.manager, dep.name))
    to_add = []
    for manager, name in libs:
        upstream = session.query(Upstream).filter_by(manager=manager, name=name).first()
        if upstream is None:
            upstream = Upstream(manager=manager, name=name)
            to_add.append(upstream)
        data = metadata.get_metadata(manager, name)
        upstream.set_description(data['description'])
        upstream.latest = data['latest']

    for add in to_add:
        session.add(add)
    # TODO: should we purge this table for libs we no longer track?

    session.commit()
