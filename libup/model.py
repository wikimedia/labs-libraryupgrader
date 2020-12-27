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
from collections import defaultdict
import gzip
import json
from sqlalchemy import BLOB, Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from typing import List, Optional

from . import config

# 2^16 per https://dev.mysql.com/doc/refman/8.0/en/storage-requirements.html
BLOB_SIZE = 65536

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

    def __lt__(self, other):
        return self.name < other.name

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

    def by_manager(self):
        ret = defaultdict(lambda: defaultdict(list))
        for dep in self.deps.values():
            ret[dep.manager][dep.mode].append(dep)

        return ret


class Repository(Base):
    """Represents a repository+branch pair"""
    __tablename__ = "repositories"
    id = Column(Integer, primary_key=True)
    name = Column(String(80), nullable=False)
    branch = Column(String(80), nullable=False)
    # Same as the most recent `log.is_error`, but in this table for speed
    is_error = Column(Boolean, nullable=False, default=False)

    logs = relationship("Log", back_populates="repository",
                        cascade="all, delete, delete-orphan")
    advisories = relationship("Advisories", back_populates="repository",
                              cascade="all, delete, delete-orphan")

    def __lt__(self, other):
        return self.name < other.name

    def key(self):
        return f"{self.name}:{self.branch}"

    def is_canary(self):
        return self.name in config.repositories()['canaries']

    def get_advisories(self, manager: str) -> Optional[Advisories]:
        for advisory in self.advisories:
            if advisory.manager == manager:
                return advisory


class Log(Base):
    """Log of a libup run"""
    __tablename__ = "logs"
    id = Column(Integer, primary_key=True)
    repo_id = Column(Integer, ForeignKey('repositories.id'))
    # Time of entry in mw time format
    time = Column(String(15), nullable=False)
    # The actual log text, might be gzipped
    text = Column(BLOB, nullable=False)
    # The patch file, if any
    patch = Column(BLOB, nullable=True)
    # Whether the run ended in an error or not
    is_error = Column(Boolean, nullable=False, default=False)

    repository = relationship("Repository", back_populates="logs")

    def __lt__(self, other):
        return self.id < other.id

    def get_text(self) -> str:
        if self.text.startswith(b'g:'):
            return gzip.decompress(self.text[2:]).decode()
        else:
            return self.text.decode()

    def set_text(self, text: str):
        encoded = text.encode()
        if len(encoded) >= BLOB_SIZE:
            self.text = b'g:' + gzip.compress(encoded)
        else:
            self.text = encoded

    def get_patch(self) -> Optional[str]:
        if self.patch is not None:
            return self.patch.decode()


class Upstream(Base):
    """Upstream metadata"""
    __tablename__ = "upstreams"
    id = Column(Integer, primary_key=True)
    # "npm" or "composer", etc.
    manager = Column(String(10), nullable=False)
    # package name
    name = Column(String(80), nullable=False)
    # upstream description
    description = Column(BLOB, nullable=False)
    # latest available version
    latest = Column(String(80), nullable=False)

    def set_description(self, desc: str):
        self.description = desc.encode()

    def get_description(self) -> str:
        return self.description.decode()

    def link(self) -> str:
        if self.manager == 'composer':
            return f"https://packagist.org/packages/{self.name}"
        elif self.manager == 'npm':
            return f"https://www.npmjs.com/package/{self.name}"
        else:
            raise RuntimeError(f"Unsupported manager: {self.manager}")


class Advisories(Base):
    """Security advisories"""
    __tablename__ = "advisories"
    id = Column(Integer, primary_key=True)
    repo_id = Column(Integer, ForeignKey('repositories.id'))
    # "npm" or "composer", etc.
    manager = Column(String(10), nullable=False)
    # The advisories, in a JSON blob
    data = Column(BLOB, nullable=False)

    repository = relationship("Repository", back_populates="advisories")

    def set_data(self, data):
        contents = json.dumps(data).encode()
        if len(contents) > BLOB_SIZE:
            self.data = b'g:' + gzip.compress(contents)
        else:
            self.data = contents

    def get_data(self):
        if self.data.startswith(b'g:'):
            contents = gzip.decompress(self.data[2:])
        else:
            contents = self.data
        return json.loads(contents.decode())
