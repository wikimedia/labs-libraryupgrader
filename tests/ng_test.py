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

import json
import os
import pytest
import re

from libup.ng import LibraryUpgrader


def test_has_npm(tempfs):
    libup = LibraryUpgrader()
    assert libup.has_npm is False
    tempfs.create_file('package.json', contents='{}')
    assert libup.has_npm is True


def test_has_composer(tempfs):
    libup = LibraryUpgrader()
    assert libup.has_composer is False
    tempfs.create_file('composer.json', contents='{}')
    assert libup.has_composer is True


def test_ensure_package_lock(tempfs, mocker):
    libup = LibraryUpgrader()
    check_call = mocker.patch.object(libup, 'check_call')
    libup.ensure_package_lock()
    check_call.assert_called_once_with(['npm', 'i', '--package-lock-only'])
    assert libup.msg_fixes == ['Committed package-lock.json (T179229) too.']
    libup = LibraryUpgrader()
    check_call = mocker.patch.object(libup, 'check_call')
    tempfs.create_file('package-lock.json', contents='{}')
    libup.ensure_package_lock()
    check_call.assert_not_called()
    assert libup.msg_fixes == []
    # TODO: .gitignore integration


def test_update_coc(tempfs):
    libup = LibraryUpgrader()
    # No CoC.md
    libup.fix_coc()
    assert libup.msg_fixes == []
    # Already correct CoC.md
    tempfs.create_file(
        'CODE_OF_CONDUCT.md',
        contents='The development of this software is covered by a [Code of Conduct]'
                 '(https://www.mediawiki.org/wiki/Special:MyLanguage/Code_of_Conduct).\n')
    libup.fix_coc()
    assert libup.msg_fixes == []


def test_actually_update_coc(tempfs):
    # The wrong CoC.md
    tempfs.create_file(
        'CODE_OF_CONDUCT.md',
        contents='The development of this software is covered by a [Code of Conduct]'
                 '(https://www.mediawiki.org/wiki/Code_of_Conduct).\n')
    libup = LibraryUpgrader()
    libup.fix_coc()
    assert 'Special:MyLanguage/Code_of_Conduct' in tempfs.contents('CODE_OF_CONDUCT.md')
    assert libup.msg_fixes == ['And updating CoC link to use Special:MyLanguage (T202047).']


def test_fix_phpcs_xml_location(tempfs, mocker):
    # No phpcs.xml nor .phpcs.xml
    libup = LibraryUpgrader()
    check_call = mocker.patch.object(libup, 'check_call')
    libup.fix_phpcs_xml_location()
    check_call.assert_not_called()
    assert libup.msg_fixes == []
    # Now if only phpcs.xml exists
    tempfs.create_file('phpcs.xml')
    libup = LibraryUpgrader()
    check_call = mocker.patch.object(libup, 'check_call')
    libup.fix_phpcs_xml_location()
    check_call.assert_called_once_with(['git', 'mv', 'phpcs.xml', '.phpcs.xml'])
    assert libup.msg_fixes == ['And moved phpcs.xml to .phpcs.xml (T177256).']


def test_fix_phpcs_xml_location_exists(tempfs, mocker):
    # Now if a .phpcs.xml exists
    tempfs.create_file('.phpcs.xml')
    libup = LibraryUpgrader()
    check_call = mocker.patch.object(libup, 'check_call')
    libup.fix_phpcs_xml_location()
    check_call.assert_not_called()
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
def test_fix_private_package_json(tempfs, repo, pkg, expected):
    libup = LibraryUpgrader()
    if pkg is not None:
        tempfs.create_file('package.json', contents=pkg)
    e_fixes = ['Set `private: true` in package.json.'] if expected else []
    libup.fix_private_package_json(repo)
    assert libup.msg_fixes == e_fixes
    if expected:
        assert tempfs.json_contents('package.json')['private'] is True


def test_root_eslintrc(tempfs):
    libup = LibraryUpgrader()
    # No .eslintrc.json
    libup.fix_root_eslintrc()
    assert libup.msg_fixes == []
    # Already set
    tempfs.create_file('.eslintrc.json', contents='{"root": true}')
    libup.fix_root_eslintrc()
    assert libup.msg_fixes == []


def test_root_eslintrc_real(tempfs):
    libup = LibraryUpgrader()
    tempfs.create_file('.eslintrc.json', contents='{}')
    libup.fix_root_eslintrc()
    assert {'root': True} == tempfs.json_contents('.eslintrc.json')
    assert libup.msg_fixes == ['Set `root: true` in .eslintrc.json (T206485).']


@pytest.mark.parametrize('scripts,expected', (
    ({}, {'fix': ['phpcbf']}),
    ({'fix': ['first']}, {'fix': ['first', 'phpcbf']}),
    ({'fix': 'first'}, {'fix': ['first', 'phpcbf']}),
))
def test_fix_composer_fix(tempfs, scripts, expected):
    tempfs.create_file('composer.json', contents=json.dumps({
        'require-dev': {
            'mediawiki/mediawiki-codesniffer': '24.0.0',
        },
        'scripts': scripts
    }))
    libup = LibraryUpgrader()
    libup.fix_composer_fix()
    assert tempfs.json_contents('composer.json')['scripts'] == expected


def test_fix_eslint_config(tempfs):
    __dir__ = os.path.dirname(__file__)
    with open(os.path.join(__dir__, 'ng_Gruntfile.js.before')) as f:
        tempfs.create_file('Gruntfile.js', contents=f.read())
    libup = LibraryUpgrader()
    libup.fix_eslint_config()
    with open(os.path.join(__dir__, 'ng_Gruntfile.js.expected')) as f:
        assert tempfs.contents('Gruntfile.js') == f.read()


def test_indent():
    libup = LibraryUpgrader()
    assert libup._indent("""
foo
bar
baz
""") == """
 foo
 bar
 baz"""


@pytest.mark.skip
def test_sha1():
    # Note: integration test, relies on this being a git checkout
    libup = LibraryUpgrader()
    sha1 = libup.sha1()
    assert re.match(r'^[0-9a-f]{40}$', sha1) is not None
