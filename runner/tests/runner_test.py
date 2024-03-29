"""
Copyright (C) 2019 Kunal Mehta <legoktm@debian.org>

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

from runner import LibraryUpgrader
from runner.update import Update


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
                 "\t<arg name=\"extensions\" value=\"php\" />\n" +
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
                 "\t<arg name=\"extensions\" value=\"php\" />\n" +
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
                 "\t<arg name=\"extensions\" value=\"php,php5\" />\n" +
                 "\t<arg name=\"encoding\" value=\"UTF-8\" />\n" +
                 "</ruleset>\n"
    )
    libup = LibraryUpgrader()
    libup.fix_phpcs_xml_configuration()
    assert 'php5' not in tempfs.contents('.phpcs.xml')
    assert libup.msg_fixes == ['Dropped .php5 files from .phpcs.xml (T200956).']


def test_fix_fix_phpcs_xml_configuration_filetypes_incremoval(tempfs):
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
    assert 'inc' not in tempfs.contents('.phpcs.xml')
    assert libup.msg_fixes == ['Dropped .inc files from .phpcs.xml (T200956).']


def test_fix_fix_phpcs_xml_configuration_filetypes_php5andincremoval(tempfs):
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
    assert 'inc' not in tempfs.contents('.phpcs.xml')
    assert libup.msg_fixes == ['Dropped .php5 and .inc files from .phpcs.xml (T200956).']


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
    assert 'inc' not in tempfs.contents('.phpcs.xml')
    assert 'Consolidated .phpcs.xml encoding to "UTF-8" (T200956).' in libup.msg_fixes
    assert 'Dropped .php5 and .inc files from .phpcs.xml (T200956).' in libup.msg_fixes


def test_fix_fix_phpcs_xml_configuration_encodingchange_and_filetypes_php5removal_whitespaces(tempfs):
    tempfs.create_file(
        '.phpcs.xml',
        contents="<?xml version=\"1.0\" encoding=\"UTF-8\"?><ruleset>\n" +
                 "\t<rule ref=\"./vendor/mediawiki/mediawiki-codesniffer/MediaWiki\"/>\n" +
                 "\t<file>.</file>\n" +
                 "\t<arg\tname=\"extensions\" value=\"php,php5,inc\"  />\n" +
                 "\t<arg name=\"encoding\"  value=\"utf-8\"/>\n" +
                 "</ruleset>\n"
    )
    libup = LibraryUpgrader()
    libup.fix_phpcs_xml_configuration()
    assert 'utf' not in tempfs.contents('.phpcs.xml')
    assert 'php5' not in tempfs.contents('.phpcs.xml')
    assert 'inc' not in tempfs.contents('.phpcs.xml')
    assert 'Consolidated .phpcs.xml encoding to "UTF-8" (T200956).' in libup.msg_fixes
    assert 'Dropped .php5 and .inc files from .phpcs.xml (T200956).' in libup.msg_fixes


def test_fix_fix_phpcs_xml_configuration_exclude_pattern_not(tempfs):
    tempfs.create_file('composer.json', contents=json.dumps({
        'require-dev': {
            'mediawiki/mediawiki-codesniffer': '35.0.0',
        },
        'scripts': {}
    }))
    tempfs.create_file(
        '.phpcs.xml',
        contents="<?xml version=\"1.0\" encoding=\"UTF-8\"?><ruleset>\n" +
                 "\t<rule ref=\"./vendor/mediawiki/mediawiki-codesniffer/MediaWiki\"/>\n" +
                 "\t<file>.</file>\n" +
                 "\t<exclude-pattern>vendor</exclude-pattern>\n" +
                 "\t<exclude-pattern>node_modules</exclude-pattern>\n" +
                 "</ruleset>\n"
    )
    libup = LibraryUpgrader()
    libup.fix_phpcs_xml_configuration()
    assert '>vendor<' in tempfs.contents('.phpcs.xml')
    assert '>node_modules<' in tempfs.contents('.phpcs.xml')
    assert 'Dropped default excluded folder(s) from .phpcs.xml (T274684).' not in libup.msg_fixes


def test_fix_fix_phpcs_xml_configuration_exclude_pattern_simple(tempfs):
    tempfs.create_file('composer.json', contents=json.dumps({
        'require-dev': {
            'mediawiki/mediawiki-codesniffer': '36.0.0',
        },
        'scripts': {}
    }))
    tempfs.create_file(
        '.phpcs.xml',
        contents="<?xml version=\"1.0\" encoding=\"UTF-8\"?><ruleset>\n" +
                 "\t<rule ref=\"./vendor/mediawiki/mediawiki-codesniffer/MediaWiki\"/>\n" +
                 "\t<file>.</file>\n" +
                 "\t<exclude-pattern>vendor</exclude-pattern>\n" +
                 "\t<exclude-pattern>node_modules</exclude-pattern>\n" +
                 "</ruleset>\n"
    )
    libup = LibraryUpgrader()
    libup.fix_phpcs_xml_configuration()
    assert '>vendor<' not in tempfs.contents('.phpcs.xml')
    assert '>node_modules<' not in tempfs.contents('.phpcs.xml')
    assert 'Dropped default excluded folder(s) from .phpcs.xml (T274684).' in libup.msg_fixes


def test_fix_fix_phpcs_xml_configuration_exclude_pattern_complex(tempfs):
    tempfs.create_file('composer.json', contents=json.dumps({
        'require-dev': {
            'mediawiki/mediawiki-codesniffer': '36.0.0',
        },
        'scripts': {}
    }))
    tempfs.create_file(
        '.phpcs.xml',
        contents="<?xml version=\"1.0\" encoding=\"UTF-8\"?><ruleset>\n" +
                 "\t<rule ref=\"./vendor/mediawiki/mediawiki-codesniffer/MediaWiki\"/>\n" +
                 "\t<file>.</file>\n" +
                 "\t<exclude-pattern type=\"relative\">^vendor/</exclude-pattern>\n" +
                 "\t<exclude-pattern type=\"relative\">^node_modules/*</exclude-pattern>\n" +
                 "</ruleset>\n"
    )
    libup = LibraryUpgrader()
    libup.fix_phpcs_xml_configuration()
    assert '^vendor' not in tempfs.contents('.phpcs.xml')
    assert '^node_modules' not in tempfs.contents('.phpcs.xml')
    assert 'Dropped default excluded folder(s) from .phpcs.xml (T274684).' in libup.msg_fixes


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
        ('mediawiki/extensions/FooBar', '{"name": "FooBar"}', True),
        ('mediawiki/extensions/FooBar', '{"name": "FooBar", "private": true}', False),
    ]
)
def test_fix_package_json_metadata(tempfs, repo, pkg, expected):
    libup = LibraryUpgrader()
    if pkg is not None:
        tempfs.create_file('package.json', contents=pkg)
    e_fixes = ['Set `private: true` in package.json.'] if expected else []
    libup.fix_package_json_metadata(repo)
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
    assert libup.msg_fixes == ['Set `root: true` in ESLint config (T206485).']


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
        "eslint-config-wikimedia": "0.16.0"
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
        "stylelint-config-wikimedia": "0.5.1",
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
    libup.fix_add_vendor_node_modules_to_gitignore('foo')
    assert tempfs.contents('.gitignore') == '/vendor/\n/node_modules/\n'
    tempfs.create_file('.gitignore', '/node_modules\n')
    libup.fix_add_vendor_node_modules_to_gitignore('foo')
    assert tempfs.contents('.gitignore') == '/node_modules\n/vendor/\n'
    tempfs.create_file('.gitignore', '/special\n')
    libup.fix_add_vendor_node_modules_to_gitignore('mediawiki/core')
    assert tempfs.contents('.gitignore') == '/special\n'


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


def test_fix_composer_irc(tempfs):
    tempfs.create_file('composer.json',
                       contents="""
    {
        "support": {
            "irc": "irc://irc.freenode.net/mediawiki"
        }
    }
    """)
    libup = LibraryUpgrader()
    libup.fix_composer_irc()
    composer = tempfs.json_contents('composer.json')
    assert composer['support']['irc'] == "irc://irc.libera.chat/mediawiki"


def test_fix_phpcs_command(tempfs):
    tempfs.create_file('composer.json',
                       contents="""
    {
        "require-dev": {
            "mediawiki/mediawiki-codesniffer": "35.0.0"
        },
        "scripts": {
            "test": [
                "parallel-lint . --exclude vendor --exclude node_modules",
                "phpcs -p -s",
                "minus-x check ."
            ]
        }
    }
    """)

    libup = LibraryUpgrader()
    libup.fix_phpcs_command()
    composer = tempfs.json_contents('composer.json')
    assert 'phpcs' in composer['scripts']
    assert 'phpcs -p -s' not in composer['scripts']['test']
    assert '@phpcs' in composer['scripts']['test']


def test_fix_phpcs_command_noop(tempfs):
    tempfs.create_file('composer.json',
                       contents="""
    {
        "scripts": {
            "test": [
                "parallel-lint . --exclude vendor --exclude node_modules"
            ]
        }
    }
    """)

    libup = LibraryUpgrader()
    libup.fix_phpcs_command()
    composer = tempfs.json_contents('composer.json')
    assert 'phpcs' not in composer['scripts']
    assert '@phpcs' not in composer['scripts']['test']


def test_fix_eslintrc_use_clientes5_profile(tempfs):
    tempfs.create_file('package.json',
                       contents="""
    {
        "devDependencies": {
            "eslint-config-wikimedia": "0.19.0"
        }
    }
    """)
    tempfs.create_file('.eslintrc.json',
                       contents="""
    {
        "root": true,
        "extends": [
            "test/test",
            "wikimedia/client",
            "wikimedia/mediawiki"
        ]
    }
    """)
    libup = LibraryUpgrader()
    libup.fix_eslintrc_use_mediawiki_profile('mediawiki/extensions/Test')
    eslintrc = tempfs.json_contents('.eslintrc.json')
    assert len(eslintrc) == 2
    # Also verifies the order didn't change
    assert eslintrc['extends'] == [
        'test/test',
        'wikimedia/client-es5',
        'wikimedia/mediawiki'
    ]


def test_fix_eslintrc_use_clientes5_profile_noop(tempfs):
    tempfs.create_file('package.json',
                       contents="""
    {
        "devDependencies": {
            "eslint-config-wikimedia": "0.15.1"
        }
    }
    """)
    tempfs.create_file('.eslintrc.json',
                       contents="""
    {
        "root": true,
        "extends": [
            "wikimedia/mediawiki",
            "wikimedia/client"
        ]
    }
    """)
    libup = LibraryUpgrader()
    libup.fix_eslintrc_use_mediawiki_profile('mediawiki/extensions/Test')
    eslintrc = tempfs.json_contents('.eslintrc.json')
    assert len(eslintrc) == 2
    assert len(eslintrc['extends']) == 2
    assert 'wikimedia/client' in eslintrc['extends']
    assert 'wikimedia/client-es5' not in eslintrc['extends']


def test_fix_eslintrc_use_mediawiki_profile_noop(tempfs):
    tempfs.create_file('package.json',
                       contents="""
    {
        "devDependencies": {
            "eslint-config-wikimedia": "0.15.1"
        }
    }
    """)
    tempfs.create_file('.eslintrc.json',
                       contents="""
    {
        "root": true,
        "extends": [
            "wikimedia/client"
        ]
    }
    """)
    libup = LibraryUpgrader()
    libup.fix_eslintrc_use_mediawiki_profile('mediawiki/extensions/Test')
    eslintrc = tempfs.json_contents('.eslintrc.json')
    assert len(eslintrc) == 2
    assert len(eslintrc['extends']) == 1
    assert 'wikimedia/mediawiki' not in eslintrc['extends']


def test_fix_eslintrc_use_mediawiki_profile(tempfs):
    tempfs.create_file('package.json',
                       contents="""
    {
        "devDependencies": {
            "eslint-config-wikimedia": "0.15.1"
        }
    }
    """)
    tempfs.create_file('.eslintrc.json',
                       contents="""
    {
        "root": true,
        "extends": [
            "wikimedia/client"
        ],
        "globals": {
            "OO": false,
            "mw": false
        }
    }
    """)
    libup = LibraryUpgrader()
    libup.fix_eslintrc_use_mediawiki_profile('mediawiki/extensions/Test')
    eslintrc = tempfs.json_contents('.eslintrc.json')
    assert len(eslintrc) == 2
    assert len(eslintrc['extends']) == 2
    assert 'wikimedia/mediawiki' in eslintrc['extends']
    assert 'wikimedia/jquery' not in eslintrc['extends']
    assert 'globals' not in eslintrc


def test_fix_eslintrc_use_mediawiki_profile_and_jquery_one_too(tempfs):
    tempfs.create_file('package.json',
                       contents="""
    {
        "devDependencies": {
            "eslint-config-wikimedia": "0.15.1"
        }
    }
    """)
    tempfs.create_file('.eslintrc.json',
                       contents="""
    {
        "root": true,
        "extends": [
            "wikimedia/client"
        ],
        "globals": {
            "$": false,
            "OO": false,
            "mw": false
        }
    }
    """)
    libup = LibraryUpgrader()
    libup.fix_eslintrc_use_mediawiki_profile('mediawiki/extensions/Test')
    eslintrc = tempfs.json_contents('.eslintrc.json')
    assert len(eslintrc) == 2
    assert len(eslintrc['extends']) == 3
    assert 'wikimedia/client' in eslintrc['extends']
    assert 'wikimedia/mediawiki' in eslintrc['extends']
    assert 'wikimedia/jquery' in eslintrc['extends']
    assert 'globals' not in eslintrc


def test_fix_eslintrc_use_mediawiki_profile_but_keep_other_stuff(tempfs):
    tempfs.create_file('package.json',
                       contents="""
    {
        "devDependencies": {
            "eslint-config-wikimedia": "0.15.1"
        }
    }
    """)
    tempfs.create_file('.eslintrc.json',
                       contents="""
    {
        "root": true,
        "extends": [
            "wikimedia/client"
        ],
        "globals": {
            "testValue": false,
            "OO": false,
            "mw": false
        }
    }
    """)
    libup = LibraryUpgrader()
    libup.fix_eslintrc_use_mediawiki_profile('mediawiki/extensions/Test')
    eslintrc = tempfs.json_contents('.eslintrc.json')
    assert len(eslintrc) == 3
    assert len(eslintrc['extends']) == 2
    assert 'wikimedia/client' in eslintrc['extends']
    assert 'wikimedia/mediawiki' in eslintrc['extends']
    assert len(eslintrc['globals']) == 1
    assert 'OO' not in eslintrc['globals']
    assert 'mw' not in eslintrc['globals']
    assert 'testValue' in eslintrc['globals']


def test_build_message():
    libup = LibraryUpgrader()
    assert libup.build_message() == '[DNM] there are no updates'
    upd = Update('manager1', 'pkg1', '0.1', '0.2')
    libup.updates.append(upd)
    assert libup.build_message() == 'build: Updating pkg1 to 0.2\n'
    libup.updates.append(Update('manager1', 'pkg2', '0.3', '0.4'))
    assert libup.build_message() == """build: Updating manager1 dependencies

* pkg1: 0.1 → 0.2
* pkg2: 0.3 → 0.4
"""
    libup.updates.append(Update('manager2', 'pkg3', '0.5', '0.6', reason='This is reason1.'))
    assert libup.build_message() == """build: Updating dependencies

manager1:
* pkg1: 0.1 → 0.2
* pkg2: 0.3 → 0.4

manager2:
* pkg3: 0.5 → 0.6
  This is reason1.

"""
    libup.msg_fixes.append('Fixed one more thing')
    assert libup.build_message() == """build: Updating dependencies

manager1:
* pkg1: 0.1 → 0.2
* pkg2: 0.3 → 0.4

manager2:
* pkg3: 0.5 → 0.6
  This is reason1.


Additional changes:
* Fixed one more thing
"""
