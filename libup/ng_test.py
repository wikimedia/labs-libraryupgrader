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

import pytest
import re
import subprocess

from .ng import LibraryUpgrader


class MockLibraryUpgrader(LibraryUpgrader):
    def __init__(self):
        super().__init__()
        self.called = []

    def check_call(self, args: list) -> str:
        self.called.append(args)
        return ' '.join(args)


def test_has_npm(fs):
    libup = LibraryUpgrader()
    assert libup.has_npm is False
    fs.create_file('package.json', contents='{}')
    assert libup.has_npm is True


def test_has_composer(fs):
    libup = LibraryUpgrader()
    assert libup.has_composer is False
    fs.create_file('composer.json', contents='{}')
    assert libup.has_composer is True


def test_check_call():
    libup = LibraryUpgrader()
    res = libup.check_call(['echo', 'hi'])
    assert res == 'hi\n'


def test_check_call_fail():
    libup = LibraryUpgrader()
    with pytest.raises(subprocess.CalledProcessError):
        libup.check_call(['false'])


def test_ensure_package_lock(fs):
    libup = MockLibraryUpgrader()
    libup.ensure_package_lock()
    assert libup.called == [['npm', 'i', '--package-lock-only']]
    assert libup.msg_fixes == ['Committed package-lock.json (T179229) too.']
    libup = MockLibraryUpgrader()
    fs.create_file('package-lock.json', contents='{}')
    libup.ensure_package_lock()
    assert libup.called == []
    assert libup.msg_fixes == []
    # TODO: .gitignore integration


def test_update_coc(fs):
    libup = LibraryUpgrader()
    # No CoC.md
    libup.fix_coc()
    assert libup.msg_fixes == []
    # Already correct CoC.md
    fs.create_file('CODE_OF_CONDUCT.md',
                   contents='The development of this software is covered by a [Code of Conduct]'
                            '(https://www.mediawiki.org/wiki/Special:MyLanguage/Code_of_Conduct).\n')
    libup.fix_coc()
    assert libup.msg_fixes == []


def test_actually_update_coc(fs):
    # The wrong CoC.md
    fs.create_file('CODE_OF_CONDUCT.md',
                   contents='The development of this software is covered by a [Code of Conduct]'
                            '(https://www.mediawiki.org/wiki/Code_of_Conduct).\n')
    libup = LibraryUpgrader()
    libup.fix_coc()
    # TODO: verify it actually fixed it
    assert libup.msg_fixes == ['And updating CoC link to use Special:MyLanguage (T202047).']


def test_fix_phpcs_xml_location(fs):
    # No phpcs.xml nor .phpcs.xml
    libup = MockLibraryUpgrader()
    libup.fix_phpcs_xml_location()
    assert libup.called == []
    assert libup.msg_fixes == []
    # Now if only phpcs.xml exists
    fs.create_file('phpcs.xml')
    libup = MockLibraryUpgrader()
    libup.fix_phpcs_xml_location()
    assert libup.called == [['git', 'mv', 'phpcs.xml', '.phpcs.xml']]
    assert libup.msg_fixes == ['And moved phpcs.xml to .phpcs.xml (T177256).']
    # Now if a .phpcs.xml exists
    fs.create_file('.phpcs.xml')
    libup = MockLibraryUpgrader()
    libup.fix_phpcs_xml_location()
    assert libup.called == []
    assert libup.msg_fixes == []


@pytest.mark.parametrize(
    'repo,pkg,expected',
    [
        ('mediawiki/extensions/FooBar', None, False),
        ('mediawiki/core', None, False),
        ('mediawiki/core', '{}', False),
        ('mediawiki/extensions/FooBar', '{}', True),
        ('mediawiki/extensions/FooBar', '{"private": true}', False),
    ]
)
def test_fix_private_package_json(fs, repo, pkg, expected):
    libup = LibraryUpgrader()
    if pkg is not None:
        fs.create_file('package.json', contents=pkg)
    e_fixes = ['Set `private: true` in package.json.'] if expected else []
    libup.fix_private_package_json(repo)
    assert libup.msg_fixes == e_fixes


@pytest.mark.skip
def test_sha1():
    # Note: integration test, relies on this being a git checkout
    libup = LibraryUpgrader()
    sha1 = libup.sha1()
    assert re.match(r'^[0-9a-f]{40}$', sha1) is not None
