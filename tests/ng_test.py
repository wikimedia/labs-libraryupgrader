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
import pytest

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


def test_fix_phpcs_xml_configuration_noop(tempfs):
    tempfs.create_file(
        '.phpcs.xml',
        contents="<?xml version=\"1.0\" encoding=\"UTF-8\"?><ruleset>\n" +
                 "\t<rule ref=\"./vendor/mediawiki/mediawiki-codesniffer/MediaWiki\" />\n" +
                 "\t<file>.</file>\n" +
                 "\t<arg name=\"extensions\" value=\"php,inc\" />\n" +
                 "\t<arg name=\"encoding\" value=\"UTF-8\" />\n" +
                 "</ruleset>\n"
    )
    libup = LibraryUpgrader()
    libup.fix_phpcs_xml_configuration()
    assert libup.msg_fixes == []


def test_fix_phpcs_xml_configuration_encodingchange(tempfs):
    tempfs.create_file(
        '.phpcs.xml',
        contents="<?xml version=\"1.0\" encoding=\"UTF-8\"?><ruleset>\n" +
                 "\t<rule ref=\"./vendor/mediawiki/mediawiki-codesniffer/MediaWiki\" />\n" +
                 "\t<file>.</file>\n" +
                 "\t<arg name=\"extensions\" value=\"php,inc\" />\n" +
                 "\t<arg name=\"encoding\" value=\"utf-8\" />\n" +
                 "</ruleset>\n"
    )
    libup = LibraryUpgrader()
    libup.fix_phpcs_xml_configuration()
    assert 'utf' not in tempfs.contents('.phpcs.xml')
    assert libup.msg_fixes == ['Consolidated .phpcs.xml encoding to "UTF-8" (T200956).']


def test_fix_fix_phpcs_xml_configuration_filetypes_php5removal(tempfs):
    tempfs.create_file(
        '.phpcs.xml',
        contents="<?xml version=\"1.0\" encoding=\"UTF-8\"?><ruleset>\n" +
                 "\t<rule ref=\"./vendor/mediawiki/mediawiki-codesniffer/MediaWiki\" />\n" +
                 "\t<file>.</file>\n" +
                 "\t<arg name=\"extensions\" value=\"php,php5,inc\" />\n" +
                 "\t<arg name=\"encoding\" value=\"UTF-8\" />\n" +
                 "</ruleset>\n"
    )
    libup = LibraryUpgrader()
    libup.fix_phpcs_xml_configuration()
    assert 'php5' not in tempfs.contents('.phpcs.xml')
    assert libup.msg_fixes == ['Dropped .php5 files from .phpcs.xml (T200956).']


def test_fix_fix_phpcs_xml_configuration_encodingchange_and_filetypes_php5removal(tempfs):
    tempfs.create_file(
        '.phpcs.xml',
        contents="<?xml version=\"1.0\" encoding=\"UTF-8\"?><ruleset>\n" +
                 "\t<rule ref=\"./vendor/mediawiki/mediawiki-codesniffer/MediaWiki\" />\n" +
                 "\t<file>.</file>\n" +
                 "\t<arg name=\"extensions\" value=\"php,php5,inc\" />\n" +
                 "\t<arg name=\"encoding\" value=\"utf-8\" />\n" +
                 "</ruleset>\n"
    )
    libup = LibraryUpgrader()
    libup.fix_phpcs_xml_configuration()
    assert 'utf' not in tempfs.contents('.phpcs.xml')
    assert 'php5' not in tempfs.contents('.phpcs.xml')
    assert 'Consolidated .phpcs.xml encoding to "UTF-8" (T200956).' in libup.msg_fixes
    assert 'Dropped .php5 files from .phpcs.xml (T200956).' in libup.msg_fixes


def test_fix_phpcs_xml_location_exists(tempfs, mocker):
    # Now if a .phpcs.xml exists
    tempfs.create_file('.phpcs.xml')
    libup = LibraryUpgrader()
    check_call = mocker.patch.object(libup, 'check_call')
    libup.fix_phpcs_xml_location()
    check_call.assert_not_called()
    assert libup.msg_fixes == []


def test_fix_eslintrc_json_location(tempfs, mocker):
    # No .eslintrc nor .eslintrc.json
    libup = LibraryUpgrader()
    check_call = mocker.patch.object(libup, 'check_call')
    libup.fix_eslintrc_json_location()
    check_call.assert_not_called()
    assert libup.msg_fixes == []
    # Now if only .eslintrc exists
    tempfs.create_file('.eslintrc')
    libup = LibraryUpgrader()
    check_call = mocker.patch.object(libup, 'check_call')
    libup.fix_eslintrc_json_location()
    check_call.assert_called_once_with(['git', 'mv', '.eslintrc', '.eslintrc.json'])
    assert libup.msg_fixes == ['Use json file extension for the eslint config file.']


def test_fix_eslintrc_json_location_exists(tempfs, mocker):
    # Now if a .eslintrc.json exists
    tempfs.create_file('.eslintrc.json')
    libup = LibraryUpgrader()
    check_call = mocker.patch.object(libup, 'check_call')
    libup.fix_eslintrc_json_location()
    check_call.assert_not_called()
    assert libup.msg_fixes == []


def test_fix_stylelintrc_json_location(tempfs, mocker):
    # No .stylelintrc nor .stylelintrc.json
    libup = LibraryUpgrader()
    check_call = mocker.patch.object(libup, 'check_call')
    libup.fix_stylelintrc_json_location()
    check_call.assert_not_called()
    assert libup.msg_fixes == []
    # Now if only .stylelintrc exists
    tempfs.create_file('.stylelintrc')
    libup = LibraryUpgrader()
    check_call = mocker.patch.object(libup, 'check_call')
    libup.fix_stylelintrc_json_location()
    check_call.assert_called_once_with(['git', 'mv', '.stylelintrc', '.stylelintrc.json'])
    assert libup.msg_fixes == ['Use json file extension for the stylelint config file.']


def test_fix_stylelintrc_json_location_exists(tempfs, mocker):
    # Now if a .stylelintrc.json exists
    tempfs.create_file('.stylelintrc.json')
    libup = LibraryUpgrader()
    check_call = mocker.patch.object(libup, 'check_call')
    libup.fix_stylelintrc_json_location()
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
    ({'fix': ['phpcbf', 'second']}, {'fix': ['second', 'phpcbf']}),
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


@pytest.mark.parametrize('version,scripts,expected', (
    ('0.6.0', {}, {'phan': 'phan -d . -p'}),
    ('0.9.0', {}, {'phan': 'phan -d . --long-progress-bar'}),
    ('0.9.0', {'phan': 'thisIsWrongAndWillNotChange'}, {'phan': 'thisIsWrongAndWillNotChange'}),
    ('0.9.0', {'fix': 'foo'}, {'phan': 'phan -d . --long-progress-bar', 'fix': 'foo'}),
    ('0.9.0', {'fix': ['foo', 'bar']}, {'phan': 'phan -d . --long-progress-bar', 'fix': ['foo', 'bar']}),
))
def test_fix_composer_phan(tempfs, version, scripts, expected):
    tempfs.create_file('composer.json', contents=json.dumps({
        'require-dev': {
            'mediawiki/mediawiki-phan-config': version,
        },
        'scripts': scripts
    }))
    libup = LibraryUpgrader()
    libup.fix_composer_phan()
    assert tempfs.json_contents('composer.json')['scripts'] == expected


def test_fix_composer_phan_noop(tempfs):
    tempfs.create_file('composer.json', contents=json.dumps({
        'require-dev': {
            'mediawiki/mediawiki-codesniffer': '24.0.0',
        },
        'scripts': {}
    }))
    libup = LibraryUpgrader()
    libup.fix_composer_phan()
    assert tempfs.json_contents('composer.json')['scripts'] == {}


def test_fix_eslint_config(tempfs):
    tempfs.create_file('Gruntfile.js',
                       contents=tempfs.fixture('ng', 'Gruntfile.js.before'))
    tempfs.create_file('package.json',
                       contents="""
{
    "devDependencies": {
        "eslint-config-wikimedia": "0.15.0"
    }
}
""")
    libup = LibraryUpgrader()
    libup.fix_eslint_config()
    assert tempfs.contents('Gruntfile.js') == \
        tempfs.fixture('ng', 'Gruntfile.js.expected')


def test_fix_remove_eslint_stylelint_if_grunt(tempfs, mocker):
    tempfs.create_file('package.json',
                       contents="""
{
    "devDependencies": {
        "grunt-eslint": "0.0.0",
        "eslint": "0.0.0",
        "grunt-stylelint": "0.0.0",
        "stylelint": "0.0.0"
    }
}
""")
    libup = LibraryUpgrader()
    # Disable shelling out/etc.
    mocker.patch.object(libup, 'check_call')
    mocker.patch('os.unlink')
    mocker.patch('shutil.rmtree')
    libup.fix_remove_eslint_stylelint_if_grunt()
    pkg = tempfs.json_contents('package.json')
    assert 'eslint' not in pkg['devDependencies']
    assert 'stylelint' not in pkg['devDependencies']


def test_fix_add_vendor_node_modules_to_gitignore(tempfs):
    tempfs.create_file('package.json')
    tempfs.create_file('composer.json')
    libup = LibraryUpgrader()
    libup.fix_add_vendor_node_modules_to_gitignore()
    assert tempfs.contents('.gitignore') == '/vendor/\n/node_modules/\n'
    tempfs.create_file('.gitignore', '/node_modules\n')
    libup.fix_add_vendor_node_modules_to_gitignore()
    assert tempfs.contents('.gitignore') == '/node_modules\n/vendor/\n'


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


def test_sha1(mocker):
    libup = LibraryUpgrader()
    check_call = mocker.patch.object(libup, 'check_call')
    check_call.return_value = \
        '44560cc7288485f23988bf2e35cc20518f37b2ee refs/remotes/origin/HEAD'
    assert '44560cc7288485f23988bf2e35cc20518f37b2ee' == libup.sha1()


@pytest.mark.parametrize('line,rule,expected', (
    (
        '\tconsole.log("foo") // eslint-disable-line',
        'no-console',
        '\tconsole.log("foo")\n',
    ),
    (
        '\tconsole.log("foo") // eslint-disable-line no-console',
        'no-console',
        '\tconsole.log("foo")\n',
    ),
    (
        '\tconsole.log("foo") // eslint-disable-line no-console,max-len',
        'no-console',
        '\tconsole.log("foo") // eslint-disable-line max-len\n',
    ),
    (
        '\tconsole.log("foo") // eslint-disable-line no-console,max-len,foo2',
        'no-console',
        '\tconsole.log("foo") // eslint-disable-line max-len, foo2\n',
    ),
    (
        '\t// eslint-disable-next-line\n\tconsole.log("foo")',
        'no-console',
        '\tconsole.log("foo")\n',
    ),
    (
        '\t// eslint-disable-next-line no-console\n\tconsole.log("foo")',
        'no-console',
        '\tconsole.log("foo")\n',
    ),
    (
        '\t// eslint-disable-next-line no-console,max-len\n\tconsole.log("foo")',
        'no-console',
        '\t// eslint-disable-next-line max-len\n\tconsole.log("foo")\n',
    ),
))
def test_remove_eslint_disable(tempfs, line, rule, expected):
    tempfs.create_file('test.js', line + '\n')
    libup = LibraryUpgrader()
    libup.remove_eslint_disable('test.js', ((1, rule),))
    assert tempfs.contents('test.js') == expected


def test_fix_phpunit_result_cache(tempfs):
    tempfs.create_file('composer.json',
                       contents="""
    {
        "require-dev": {
            "phpunit/phpunit": "0.0.0"
        }
    }
    """)
    tempfs.create_file('.gitignore')
    libup = LibraryUpgrader()
    libup.fix_phpunit_result_cache()
    assert tempfs.contents('.gitignore') == '/.phpunit.result.cache\n'
    # Reset
    libup.msg_fixes = []
    libup.fix_phpunit_result_cache()
    # It didn't run again to add it
    assert libup.msg_fixes == []


def test_fix_php_parallel_lint_migration(tempfs):
    tempfs.create_file('composer.json',
                       contents="""
    {
        "require-dev": {
            "jakub-onderka/php-parallel-lint": "0.1.0",
            "jakub-onderka/php-console-highlighter": "0.2.0"
        }
    }
    """)
    libup = LibraryUpgrader()
    libup.fix_php_parallel_lint_migration()
    composer = tempfs.json_contents('composer.json')
    assert 'php-parallel-lint/php-parallel-lint' in composer['require-dev']
    assert 'jakub-onderka/php-parallel-lint' not in composer['require-dev']
    assert composer['require-dev']['php-parallel-lint/php-parallel-lint'] == '0.1.0'
    assert 'php-parallel-lint/php-console-highlighter' in composer['require-dev']
    assert 'jakub-onderka/php-console-highlighter' not in composer['require-dev']
    assert composer['require-dev']['php-parallel-lint/php-console-highlighter'] == '0.2.0'


def test_fix_phan_taint_check_plugin_merge_to_phan_old(tempfs):
    tempfs.create_file('composer.json',
                       contents="""
    {
        "require-dev": {
            "mediawiki/mediawiki-phan-config": "0.9.2"
        },
        "extra": {
            "phan-taint-check-plugin": "2.0.1"
        }
    }
    """)
    libup = LibraryUpgrader()
    libup.fix_phan_taint_check_plugin_merge_to_phan()
    composer = tempfs.json_contents('composer.json')
    assert 'phan-taint-check-plugin' in composer['extra']


def test_fix_phan_taint_check_plugin_merge_to_phan_current(tempfs):
    tempfs.create_file('composer.json',
                       contents="""
    {
        "require-dev": {
            "mediawiki/mediawiki-phan-config": "0.10.0"
        },
        "extra": {
            "phan-taint-check-plugin": "2.0.1"
        }
    }
    """)
    libup = LibraryUpgrader()
    libup.fix_phan_taint_check_plugin_merge_to_phan()
    composer = tempfs.json_contents('composer.json')
    assert 'extra' not in composer
