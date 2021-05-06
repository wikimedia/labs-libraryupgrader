"""
Copyright (C) 2020-2021 Kunal Mehta <legoktm@debian.org>

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
import hashlib
import json
from sqlalchemy import Boolean, Column, ForeignKey, Integer, LargeBinary, String
from sqlalchemy.dialects.mysql import MEDIUMBLOB
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from typing import List, Optional

from . import utils

Base = declarative_base()


class Dependency(Base):
    __tablename__ = "dependencies"
    id = Column(Integer, primary_key=True)
    name = Column(String(80), nullable=False)
    version = Column(String(150), nullable=False)
    manager = Column(String(20), nullable=False)  # "composer", "npm", etc.
    mode = Column(String(4), nullable=False)  # "prod" or "dev"
    repo_id = Column(Integer, ForeignKey('repositories.id'))

    repository = relationship("Repository", back_populates="dependencies")

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
    # Whether bundled in the tarball
    is_bundled = Column(Boolean, nullable=False, default=False)
    # Whether Wikimedia deployed
    is_wm_deployed = Column(Boolean, nullable=False, default=False)
    # Whether it's a libup canary
    is_canary = Column(Boolean, nullable=False, default=False)

    logs = relationship("Log", back_populates="repository",
                        cascade="all, delete, delete-orphan", uselist=True)
    advisories = relationship("Advisories", back_populates="repository",
                              cascade="all, delete, delete-orphan", uselist=True)
    dependencies = relationship("Dependency", back_populates="repository",
                                cascade="all, delete, delete-orphan", uselist=True)

    def __lt__(self, other):
        return self.name < other.name

    def key(self):
        return f"{self.name}:{self.branch}"

    def get_advisories(self, manager: str) -> Optional[Advisories]:
        for advisory in self.advisories:
            if advisory.manager == manager:
                return advisory
        return None


class Log(Base):
    """Log of a libup run"""
    __tablename__ = "logs"
    id = Column(Integer, primary_key=True)
    repo_id = Column(Integer, ForeignKey('repositories.id'))
    # Time of entry in mw time format
    time = Column(String(15), nullable=False)
    # The actual log text (possibly compressed)
    text = Column(LargeBinary().with_variant(MEDIUMBLOB, 'mysql'), nullable=False)  # type: ignore
    # The patch file, if any (possibly compressed)
    patch = Column(LargeBinary().with_variant(MEDIUMBLOB, 'mysql'), nullable=True)  # type: ignore
    # Whether the run ended in an error or not
    is_error = Column(Boolean, nullable=False, default=False)
    # Comma-separated hashtags to apply to the commit, if any
    hashtags = Column(LargeBinary, nullable=True)
    # sha1 of the commit this one is based on top of
    sha1 = Column(String(40), nullable=True)

    repository = relationship("Repository", back_populates="logs")

    def __lt__(self, other):
        return self.id < other.id

    def get_text(self) -> str:
        return utils.maybe_decompress(self.text)

    def set_text(self, text: str):
        self.text = utils.maybe_compress(text)

    def text_digest(self) -> str:
        sha256 = hashlib.sha256()
        sha256.update(self.get_text().encode())
        return sha256.hexdigest()

    def get_patch(self) -> Optional[str]:
        if self.patch is not None:
            return utils.maybe_decompress(self.patch)
        else:
            return None

    def set_patch(self, patch: Optional[str]):
        if patch is not None:
            self.patch = utils.maybe_compress(patch)

    def patch_digest(self) -> Optional[str]:
        patch = self.get_patch()
        if patch is None:
            return None
        sha256 = hashlib.sha256()
        sha256.update(patch.encode())
        return sha256.hexdigest()

    def get_hashtags(self) -> List[str]:
        if self.hashtags is None:
            return []
        return self.hashtags.decode().split(',')

    def set_hashtags(self, hashtags: List[str]):
        self.hashtags = ','.join(hashtags).encode()


class Upstream(Base):
    """Upstream metadata"""
    __tablename__ = "upstreams"
    id = Column(Integer, primary_key=True)
    # "npm" or "composer", etc.
    manager = Column(String(10), nullable=False)
    # package name
    name = Column(String(80), nullable=False)
    # upstream description
    description = Column(LargeBinary, nullable=False)
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
    # The advisories, in a JSON blob (possibly compressed)
    data = Column(LargeBinary, nullable=False)

    repository = relationship("Repository", back_populates="advisories")

    def set_data(self, data):
        self.data = utils.maybe_compress(json.dumps(data))

    def get_data(self):
        return json.loads(utils.maybe_decompress(self.data))


class Monitoring(Base):
    """Phabricator release monitoring"""
    __tablename__ = "monitoring"
    id = Column(Integer, primary_key=True)
    # unique key in config
    name = Column(String(30), nullable=False)
    # latest version that we fetched
    version = Column(String(80), nullable=True)
    # Current Phabricator task
    task = Column(String(10), nullable=True)
