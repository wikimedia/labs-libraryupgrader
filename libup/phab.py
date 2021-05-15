"""
Copyright (C) 2021 Kunal Mehta <legoktm@debian.org>

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
import json
from phabricator import Phabricator
from typing import List

from . import config


def get_phab() -> Phabricator:
    token = config.private()["phab_token"]
    phab = Phabricator(host="https://phabricator.wikimedia.org/api/", token=token)
    phab.update_interfaces()
    return phab


def project_phid(phab: Phabricator, slug: str) -> str:
    result = phab.project.query(slugs=[slug])
    if not result['data']:
        raise RuntimeError(f"No projects found with slug: {slug}")
    return list(result['data'])[0]


def create_task(phab: Phabricator, title: str, desc: str, projects: List[str]) -> str:
    phids = [project_phid(phab, slug) for slug in projects]
    result = phab.maniphest.createtask(title=title, description=desc, projectPHIDs=phids)
    if not result.get("id"):
        resp = json.dumps(result)
        raise RuntimeError(f"No task ID returned: {resp}")
    return f"T{result['id']}"


def add_comment(phab: Phabricator, task: str, comment: str):
    task_id = int(task[1:])
    result = phab.maniphest.update(id=task_id, comments=comment)
    if not result.get("id"):
        resp = json.dumps(result)
        raise RuntimeError(f"Failed to leave comment on {task}: {resp}")


def is_closed(phab: Phabricator, task: str) -> bool:
    task_id = int(task[1:])
    result = phab.maniphest.query(ids=[task_id])
    if not result:
        raise RuntimeError(f"Could not find task {task}")
    return list(result.values())[0]['isClosed']
