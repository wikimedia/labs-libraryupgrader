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

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .model import Dependency, Dependencies


Session = sessionmaker()


def connect():
    if os.path.exists('/etc/mariadb_password'):
        with open('/etc/mariadb_password') as f:
            pw = f.read().strip()
    else:
        pw = "password"
    # Keep in sync with alembic.ini (TODO: is there a better way to do this?)
    engine = create_engine(
        f"mysql+pymysql://libup:{pw}@localhost/libup?charset=utf8mb4"
    )
    Session.configure(bind=engine)
    return engine


def update_dependencies(repo, branch, deps):
    if not deps:
        return

    to_delete = []
    to_add = []

    connect()
    session = Session()
    existing = Dependencies(session.query(Dependency).filter_by(repo=repo, branch=branch).all())
    for dep in deps:
        found = existing.pop(dep)
        if not found:
            to_add.append(dep)
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
    for add in to_add:
        session.add(add)
    for delete in to_delete:
        session.delete(delete)

    session.commit()
