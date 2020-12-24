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

from __future__ import annotations
from sqlalchemy import BLOB, Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from typing import List, Optional

from . import config

Base = declarative_base()


class Dependency(Base):
    __tablename__ = "dependencies"
    id = Column(Integer, primary_key=True)
    name = Column(String(80), nullable=False)
    version = Column(String(150), nullable=False)
    manager = Column(String(20), nullable=False)  # "composer", "npm", etc.
    mode = Column(String(4), nullable=False)  # "prod" or "dev"
    repo = Column(String(150), nullable=False)  # TODO: normalize?
    branch = Column(String(30), nullable=False)  # TODO: normalize or combine with repo?

    def key(self):
        return f"{self.mode}:{self.manager}:{self.name}"

    def same_package(self, other: Dependency):
        """whether other is the same package"""
        return self.name == other.name and self.manager == other.manager and self.mode == self.mode

    def same_version(self, other: Dependency):
        """whether other is the same package and version"""
        return self.same_package(other) and self.version == other.version


class Dependencies:
    """container around multiple dependencies"""
    def __init__(self, deps: List[Dependency]):
        self.deps = {}
        for dep in deps:
            self.deps[dep.key()] = dep

    def find(self, dep: Dependency) -> Optional[Dependency]:
        return self.deps.get(dep.key())

    def pop(self, dep: Dependency) -> Optional[Dependency]:
        try:
            return self.deps.pop(dep.key())
        except KeyError:
            return None

    def all(self) -> List[Dependency]:
        return list(self.deps.values())


class Repository(Base):
    """Represents a repository+branch pair"""
    __tablename__ = "repositories"
    id = Column(Integer, primary_key=True)
    name = Column(String(80), nullable=False)
    branch = Column(String(80), nullable=False)
    # Same as the most recent `log.is_error`, but in this table for speed
    is_error = Column(Boolean, nullable=False, default=False)

    logs = relationship("Log", back_populates="repositories",
                        cascade="all, delete, delete-orphan")

    def key(self):
        return f"{self.name}:{self.branch}"

    def is_canary(self):
        return self.name in config.repositories()['canaries']


class Log(Base):
    """Log of a libup run"""
    __tablename__ = "logs"
    id = Column(Integer, primary_key=True)
    repo_id = Column(Integer, ForeignKey('repositories.id'))
    # Time of entry in mw time format
    time = Column(String(15), nullable=False)
    # The actual log text
    text = Column(BLOB, nullable=False)
    # The patch file, if any
    patch = Column(BLOB, nullable=True)
    # Whether the run ended in an error or not
    is_error = Column(Boolean, nullable=False, default=False)

    repositories = relationship("Repository", back_populates="logs")
