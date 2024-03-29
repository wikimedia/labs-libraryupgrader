#!/usr/bin/env python3
"""
the libup runner

Copyright (C) 2019-2021 Kunal Mehta <legoktm@debian.org>

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

import argparse
from collections import defaultdict, OrderedDict
import json
import os
import re
import shutil
import subprocess
import tempfile
import traceback
from typing import List, Tuple
from xml.etree import ElementTree

from pathlib import Path

import requests

from . import grunt, library, shell2
from .collections import SaveDict
from .files import ComposerJson, PackageJson, PackageLockJson, load_ordered_json, save_pretty_json
from .httpplan import HTTPPlan
from .update import Update

WEIGHT_NEEDED = 10  # Need to hit this score to trigger an update
RULE = '<rule ref="./vendor/mediawiki/mediawiki-codesniffer/MediaWiki">'
RULE_NO_EXCLUDE = r'<rule (ref="(?:\./)?vendor/mediawiki/mediawiki-codesniffer/MediaWiki")(?: )?/>'
FIND_RULE = re.compile(
    '(' + re.escape(RULE) + '(.*?)' + re.escape('</rule>') +
    '|' + RULE_NO_EXCLUDE +
    ')',
    re.DOTALL
)
WB_RULE = '<rule ref="./vendor/wikibase/wikibase-codesniffer/Wikibase">'
WB_RULE_NO_EXCLUDE = r'<rule (ref="(?:\./)?vendor/wikibase/wikibase-codesniffer/Wikibase")(?: )?/>'
WB_FIND_RULE = re.compile(
    '(' + re.escape(WB_RULE) + '(.*?)' + re.escape('</rule>') +
    '|' + WB_RULE_NO_EXCLUDE +
    ')',
    re.DOTALL
)
ESLINT_DISABLE_RULE = re.compile(r"\(no problems were reported from '(.*?)'\)")
ESLINT_DISABLE_LINE = re.compile(r'// eslint-disable-(next-)?line( (.*?))?$')


class LibraryUpgrader(shell2.ShellMixin):
    def __init__(self):
        self.msg_fixes = []
        self.updates = []  # type: List[Update]
        self.cves = set()
        self.output = None  # type: SaveDict
        self.weight = 0
        self.git_branch = 'main'  # Overridden later

    def log(self, text: str):
        print(text)
        if self.output:
            self.output['log'].append(text)
            # FIXME: this shouldn't be needed
            self.output.save()

    def log_update(self, upd: Update):
        self.updates.append(upd)
        self.log('Upgrading %s:%s from %s -> %s'
                 % (upd.manager[0], upd.name, upd.old, upd.new))

    @property
    def has_npm(self):
        return os.path.exists('package.json')

    @property
    def has_composer(self):
        return os.path.exists('composer.json')

    def ensure_package_lock(self):
        if not os.path.exists('package-lock.json'):
            self.check_call(['npm', 'i', '--package-lock-only'])
            self.check_package_lock()
            self.log('Editing .gitignore to remove package-lock.json')
            # We want to commit these now, so remove it from gitignore if it's in there
            if os.path.exists('.gitignore'):
                with open('.gitignore') as f:
                    ignore = f.read()
                if 'package-lock.json' in ignore:
                    ignore = re.sub(r'/?package-lock\.json\n', '', ignore)
                    with open('.gitignore', 'w') as f:
                        f.write(ignore)
            self.msg_fixes.append('Committed package-lock.json (T179229) too.')

    def ensure_composer_lock(self):
        if not os.path.exists('composer.lock'):
            self.check_call(['composer', 'install'])

    def npm_deps(self):
        if not self.has_npm:
            return None
        with open('package.json') as f:
            pkg = json.load(f)
        return {
            'deps': pkg.get('dependencies', {}),
            'dev': pkg.get('devDependencies', {}),
        }

    def composer_deps(self):
        if not self.has_composer:
            return None
        with open('composer.json') as f:
            pkg = json.load(f)
        ret = {
            'deps': pkg.get('require', {}),
            'dev': pkg.get('require-dev', {}),
        }
        if 'phan-taint-check-plugin' in pkg.get('extra', {}):
            ret['dev']['mediawiki/phan-taint-check-plugin'] \
                = pkg['extra']['phan-taint-check-plugin']
        return ret

    def npm_audit(self):
        if not self.has_npm:
            return {}
        self.ensure_package_lock()
        output = self.check_call(['npm', 'audit', '--json', '--legacy-peer-deps'], ignore_returncode=True)
        try:
            return json.loads(output)
        except json.decoder.JSONDecodeError:
            self.log('Error, invalid JSON from npm audit, skipping')
            return {'error': output}

    def composer_audit(self):
        if not self.has_composer:
            return {}
        self.ensure_composer_lock()
        # if there are no dependencies whatsoever, then no lockfile
        # will be created
        if not os.path.exists('composer.lock'):
            return {}
        req = requests.post(
            'https://php-security-checker.toolforge.org/',
            files={'lock': open('composer.lock', 'rb')},
            headers={'Accept': 'application/json'}
        )
        req.raise_for_status()
        return req.json()

    def cargo_audit(self):
        if not Path("Cargo.lock").exists():
            return {}
        output = self.check_call(["cargo-audit", "audit", "--json"], ignore_returncode=True)
        return json.loads(output)

    def npm_audit_fix(self, audit: dict):
        if not self.has_npm or not audit.get("vulnerabilities"):
            return
        self.log('Attempting to npm audit fix')
        prior = PackageJson('package.json')
        prior_lock = PackageLockJson()
        dry_run = json.loads(self.check_call(
            ['npm', 'audit', 'fix', '--dry-run', '--only=dev', '--json', '--legacy-peer-deps'],
            ignore_returncode=True
        ))
        # Debug what's going on (see T228173)
        self.log(json.dumps(dry_run))
        if dry_run['audit']['auditReportVersion'] != 2:
            raise RuntimeError(f"Unknown auditReportVersion: {dry_run['audit']['auditReportVersion']}")

        def find_fixed(name: str) -> dict:
            """Recursively walk down "via" tree"""
            fixed = {}
            info = dry_run['audit']['vulnerabilities'][name]
            if info['fixAvailable'] is not True:
                # Fix not available, so it's not valid. Maybe?
                return {}
            for via in info['via']:
                if type(via) == dict:
                    # An actual advisory
                    fixed[via["source"]] = via
                else:
                    # type(via) == str
                    fixed.update(find_fixed(via))
            return fixed

        # Before we actually fix, deps pinned in package.json need to be bumped
        current = PackageJson('package.json')
        for pkg, info in dry_run['audit']['vulnerabilities'].items():
            prior_version = prior.get_version(pkg)
            if prior_version is None:
                continue
            if type(info['fixAvailable']) == dict \
                    and info['fixAvailable']['name'] == pkg \
                    and not info['fixAvailable']['isSemVerMajor']:
                # Our package and not a major semver bump
                current.set_version(pkg, info['fixAvailable']['version'])
                fixed = find_fixed(pkg)
                self.log(json.dumps(fixed))
                reason = ''
                for _, adv_info in sorted(fixed.items()):
                    # FIXME: Add CVEs here
                    reason += f'* {adv_info["url"]}\n'
                    # TODO: line wrapping?

                upd = Update(
                    'npm',
                    pkg,
                    prior_version,
                    info['fixAvailable']['version'],
                    reason
                )
                self.log_update(upd)
                # Force a patch to be pushed
                self.weight += 10

        current.save()

        # When removing --only=dev also remove dev check to get all reasons
        self.check_call(['npm', 'audit', 'fix', '--only=dev', '--legacy-peer-deps'], ignore_returncode=True)
        current_lock = PackageLockJson('package-lock.json')

        self.fix_stupid_npm_resolved()
        self.check_package_lock()

        # Verify that tests still pass
        self.log('Verifying that tests still pass')
        self.check_call(['npm', 'ci', '--legacy-peer-deps'])
        self.check_call(['npm', 'test'])

        for pkg, info in dry_run['audit']['vulnerabilities'].items():
            if info['fixAvailable'] is not True:
                # Not fixable
                continue
            fixed = find_fixed(pkg)
            self.log(json.dumps(fixed))
            reason = ''
            if not fixed:
                continue
            for _, adv_info in sorted(fixed.items()):
                # FIXME: Add CVEs here
                reason += f'* {adv_info["url"]}\n'
                # TODO: line wrapping?

            prior_version = prior.get_version(pkg)
            if prior_version is None:
                # Try looking in the lockfile?
                prior_version = prior_lock.get_version(pkg)
            new_version = current.get_version(pkg)
            if new_version is None:
                # Try looking in the lockfile?
                new_version = current_lock.get_version(pkg)

            if prior_version == new_version:
                # Sometimes `npm audit fix` reports vulnerabilities as fixable that it can't actually fix
                continue

            upd = Update(
                'npm',
                pkg,
                prior_version,
                new_version,
                reason
            )
            self.log_update(upd)
            # Force a patch to be pushed
            self.weight += 10

    def npm_test(self):
        if not self.has_npm:
            return
        self.ensure_package_lock()
        self.check_call(['npm', 'ci', '--legacy-peer-deps'])
        self.check_call(['npm', 'test'])

    def check_package_lock(self):
        if Path('package-lock.json').exists():
            self.check_call(['package-lock-lint', 'package-lock.json'])

    def composer_test(self):
        if not self.has_composer:
            return
        self.check_call(['composer', 'install'])
        self.check_call(['composer', 'test'])

    def fix_coc(self):
        if not os.path.exists('CODE_OF_CONDUCT.md'):
            return

        with open('CODE_OF_CONDUCT.md') as f:
            old = f.read()
        new = old.replace(
            'https://www.mediawiki.org/wiki/Code_of_Conduct',
            'https://www.mediawiki.org/wiki/Special:MyLanguage/Code_of_Conduct'
        )
        if new == old:
            # No changes made
            return

        with open('CODE_OF_CONDUCT.md', 'w') as f:
            f.write(new)

        self.msg_fixes.append('And updating CoC link to use Special:MyLanguage (T202047).')

    def fix_phpcs_xml_location(self):
        if os.path.exists('phpcs.xml') and not os.path.exists('.phpcs.xml'):
            self.check_call(['git', 'mv', 'phpcs.xml', '.phpcs.xml'])
            self.msg_fixes.append('And moved phpcs.xml to .phpcs.xml (T177256).')

    def fix_phpcs_xml_configuration(self):
        if os.path.exists('.phpcs.xml'):
            ENCODING_RE = re.compile(r"^(\s*<arg\s+name=\"encoding\"\s+value=\")((?!UTF-8)\S*)(\"\s*/>)$", re.MULTILINE)

            PHP5_RE = re.compile(r"^(\s*<arg\s+name=\"extensions\"\s+value=\".*)(,php5)(.*\"\s*/>)$", re.MULTILINE)
            INC_RE = re.compile(r"^(\s*<arg\s+name=\"extensions\"\s+value=\".*)(,inc)(.*\"\s*/>)$", re.MULTILINE)

            EXCLUDE_PATTERN_RE = re.compile(r"^\s*<exclude-pattern\s*(?:type=\"relative\")?>\^?\*?\/?"
                                            "(?:\\.git|coverage|node_modules|vendor)\/?\*?<\/exclude-pattern>(\r?\n|$)",
                                            re.MULTILINE)

            with open('.phpcs.xml', 'r') as f:
                phpcs_xml = f.read()
            changes = False

            if not phpcs_xml.endswith('\n'):
                phpcs_xml += '\n'
                # Don't set changes true just for this; wait for a real change.

            if ENCODING_RE.search(phpcs_xml):
                phpcs_xml = re.sub(ENCODING_RE, r'\1UTF-8\3', phpcs_xml)
                changes = True
                self.msg_fixes.append('Consolidated .phpcs.xml encoding to "UTF-8" (T200956).')

            if PHP5_RE.search(phpcs_xml) and INC_RE.search(phpcs_xml):
                phpcs_xml = re.sub(PHP5_RE, r'\1\3', phpcs_xml)
                phpcs_xml = re.sub(INC_RE, r'\1\3', phpcs_xml)
                changes = True
                self.msg_fixes.append('Dropped .php5 and .inc files from .phpcs.xml (T200956).')
            else:
                if PHP5_RE.search(phpcs_xml):
                    phpcs_xml = re.sub(PHP5_RE, r'\1\3', phpcs_xml)
                    changes = True
                    self.msg_fixes.append('Dropped .php5 files from .phpcs.xml (T200956).')

                if INC_RE.search(phpcs_xml):
                    phpcs_xml = re.sub(INC_RE, r'\1\3', phpcs_xml)
                    changes = True
                    self.msg_fixes.append('Dropped .inc files from .phpcs.xml (T200956).')

            if self.has_composer:
                composer = ComposerJson('composer.json')
                cs_version = composer.get_version('mediawiki/mediawiki-codesniffer')
                if cs_version and library.is_greater_than_or_equal_to('36.0.0', cs_version) and \
                        EXCLUDE_PATTERN_RE.search(phpcs_xml):
                    phpcs_xml = re.sub(EXCLUDE_PATTERN_RE, r'', phpcs_xml)
                    changes = True
                    self.msg_fixes.append('Dropped default excluded folder(s) from .phpcs.xml (T274684).')

            if changes:
                with open('.phpcs.xml', 'w') as f:
                    f.write(phpcs_xml)

    def fix_eslintrc_json_location(self):
        if os.path.exists('.eslintrc') and not os.path.exists('.eslintrc.json'):
            self.check_call(['git', 'mv', '.eslintrc', '.eslintrc.json'])
            self.msg_fixes.append('Use json file extension for the eslint config file.')

    def fix_stylelintrc_json_location(self):
        if os.path.exists('.stylelintrc') and not os.path.exists('.stylelintrc.json'):
            self.check_call(['git', 'mv', '.stylelintrc', '.stylelintrc.json'])
            self.msg_fixes.append('Use json file extension for the stylelint config file.')

    def fix_composer_fix(self):
        if not self.has_composer:
            return
        composerjson = ComposerJson('composer.json')
        if composerjson.get_version('mediawiki/mediawiki-codesniffer') is None and \
                composerjson.get_version('wikibase/wikibase-codesniffer') is None:
            return
        changes = False
        j = composerjson.data
        if 'fix' not in j['scripts']:
            j['scripts']['fix'] = []
        elif not isinstance(j['scripts']['fix'], list):
            # It's a str
            j['scripts']['fix'] = [j['scripts']['fix']]

        if 'phpcbf' not in j['scripts']['fix']:
            j['scripts']['fix'].append('phpcbf')
            self.msg_fixes.append('Also added phpcbf to "composer fix" command.')
            changes = True
        elif j['scripts']['fix'][-1] != 'phpcbf':
            # Make sure phpcbf is last
            j['scripts']['fix'].remove('phpcbf')
            j['scripts']['fix'].append('phpcbf')
            self.msg_fixes.append('Also sorted "composer fix" command to run phpcbf last.')
            changes = True

        if changes:
            composerjson.data = j
            composerjson.save()

    def fix_composer_phan(self):
        if not self.has_composer:
            return

        composerjson = ComposerJson('composer.json')
        phanVersion = composerjson.get_version('mediawiki/mediawiki-phan-config')
        if phanVersion is None:
            return

        j = composerjson.data
        if 'phan' not in j['scripts']:
            if not library.is_greater_than_or_equal_to('0.9.0', phanVersion):
                phanCommand = 'phan -d . -p'
            else:
                phanCommand = 'phan -d . --long-progress-bar'

            j['scripts']['phan'] = phanCommand
            self.msg_fixes.append('Added the "composer phan" command to conveniently run phan.')
            composerjson.data = j
            composerjson.save()

    def fix_package_json_metadata(self, repo):
        if not repo.startswith(('mediawiki/extensions/', 'mediawiki/skins/')):
            # Only MW extensions and skins
            return
        if not self.has_npm:
            return
        pkg = PackageJson('package.json')
        if 'private' not in pkg.data:
            pkg.data['private'] = True
            # Move to top (but likely below name)
            pkg.data.move_to_end('private', last=False)
            pkg.save()
            self.msg_fixes.append('Set `private: true` in package.json.')
        if 'name' not in pkg.data:
            pkg.data['name'] = os.path.basename(repo)
            # Move to top
            pkg.data.move_to_end('name', last=False)
            pkg.save()
            self.msg_fixes.append('Set `name` in package.json.')

    def fix_root_eslintrc(self):
        try:
            source, data = self._get_eslint_config()
        except RuntimeError:
            return
        if 'root' in data:
            return
        data['root'] = True
        data.move_to_end('root', last=False)
        self._save_eslint_config(source, data)
        self.msg_fixes.append('Set `root: true` in ESLint config (T206485).')

    def fix_eslintrc_use_mediawiki_profile(self, repo):
        if not repo.startswith(('mediawiki/extensions/', 'mediawiki/skins/')):
            # Only MW extensions and skins
            return
        if not self.is_main():
            # TODO: once this auto-fixes newly failing rules, re-enable for release branches
            return
        try:
            source, data = self._get_eslint_config()
        except RuntimeError:
            return
        pkg = PackageJson('package.json')
        cfg_version = pkg.get_version('eslint-config-wikimedia')
        if cfg_version is None:
            # Not using our config??
            return
        elif not library.is_greater_than_or_equal_to("0.15.0", cfg_version):
            # wikimedia/mediawiki profile introduced in 0.15.0
            return

        if 'extends' not in data:
            # Something's wrong. Let's do nothing rather than make things worse.
            return

        # If it's a string, turn it into an array
        if isinstance(data['extends'], str):
            data['extends'] = [data['extends']]

        # wikimedia/client-es5 profile introduced in 0.19.0
        if library.is_greater_than_or_equal_to("0.19.0", cfg_version) \
                and 'wikimedia/client' in data['extends']:
            # Replace in the same position to reduce diff
            pos = data['extends'].index('wikimedia/client')
            data['extends'].remove('wikimedia/client')
            data['extends'].insert(pos, 'wikimedia/client-es5')
            self.msg_fixes.append('eslint: Renamed `wikimedia/client` profile to `client-es5` (T277085).')

        if 'globals' in data:
            fixed_mw_globals = []
            for fixable in ['mw', 'OO', 'require', 'module']:
                if fixable in data['globals']:
                    del data['globals'][fixable]
                    fixed_mw_globals.append(fixable)
            if '$' in data['globals']:
                if 'wikimedia/jquery' not in data['extends']:
                    data['extends'].append('wikimedia/jquery')
                    self.msg_fixes.append('eslint: Added `wikimedia/jquery` profile (T262222).')
                del data['globals']['$']
                self.msg_fixes.append('eslint: Removed global `$`, included in `wikimedia/jquery` profile (T262222).')
            if fixed_mw_globals:
                if 'wikimedia/mediawiki' not in data['extends']:
                    data['extends'].append('wikimedia/mediawiki')
                    self.msg_fixes.append('eslint: Added `wikimedia/mediawiki` profile (T262222).')
                if len(fixed_mw_globals) == 1:
                    msg = 'eslint: Removed global `{}`, included via `wikimedia/mediawiki` profile (T262222).'.format(
                        fixed_mw_globals[0])
                else:
                    msg = 'eslint: Removed globals `{}`, included via `wikimedia/mediawiki` profile (T262222).'.format(
                        '`, `'.join(fixed_mw_globals))
                self.msg_fixes.append(msg)
            if not data['globals']:
                del data['globals']
                self.msg_fixes.append('eslint: Dropped the empty global definition.')

        self._save_eslint_config(source, data)

    def fix_eslint_config(self):
        if not os.path.exists('Gruntfile.js'):
            return
        gf = grunt.Gruntfile()
        try:
            data = gf.parse_section('eslint')
        except grunt.NoSuchSection:
            return
        except:  # noqa
            # Some bug with the parser
            tb = traceback.format_exc()
            self.log(tb)
            return

        changes = False
        if 'options' not in data:
            data['options'] = OrderedDict()
            data.move_to_end('options', last=False)
        set_options_cache = False
        if 'cache' not in data['options']:
            data['options']['cache'] = True
            self.msg_fixes.append('Enable eslint caching.')
            changes = True
            set_options_cache = True
        if data['options']['cache'] and os.path.exists('.gitignore'):
            # TODO: implement abstraction for .gitignore
            with open('.gitignore') as f:
                gitignore = f.read()
            if not gitignore.endswith('\n'):
                gitignore += '\n'
                # Don't set changes true just for this; wait for a real change.
            if '.eslintcache' not in gitignore:
                gitignore += '/.eslintcache\n'
                changes = True
            if changes:
                with open('.gitignore', 'w') as f:
                    f.write(gitignore)
                if not set_options_cache:
                    self.msg_fixes.append('Added .eslintcache to .gitignore.')
        pkg = PackageJson('package.json')
        eslint_cfg = pkg.get_version('eslint-config-wikimedia')
        if eslint_cfg and 'reportUnusedDisableDirectives' in data['options'] \
                and data['options']['reportUnusedDisableDirectives'] \
                and (eslint_cfg == '0.15.0' or library.is_greater_than('0.15.0', eslint_cfg)):
            del data['options']['reportUnusedDisableDirectives']
            self.msg_fixes.append('Removing manual reportUnusedDisableDirectives for eslint.')
            changes = True
        if eslint_cfg and data['options'].get('extensions') == ['.js', '.json'] \
                and library.is_greater_than_or_equal_to('0.16.0', eslint_cfg):
            del data['options']['extensions']
            self.msg_fixes.append('Removing manual extensions for eslint.')
            changes = True

        if changes:
            gf.set_section('eslint', data)
            gf.save()

    def fix_remove_eslint_stylelint_if_grunt(self):
        """see T242145"""
        if not self.has_npm:
            return
        pkg = PackageJson('package.json')
        changes = False
        if pkg.get_version('grunt-eslint') and pkg.get_version('eslint'):
            pkg.remove_package('eslint')
            changes = True
            self.msg_fixes.append('Remove direct "eslint" dependency in favor of "grunt-eslint".')

        if pkg.get_version('eslint-config-wikimedia') and pkg.get_version('eslint-config-node-services'):
            pkg.remove_package('eslint-config-node-services')
            changes = True
            msg = 'Remove deprecated "eslint-config-node-services" in favor of "eslint-config-wikimedia".'
            self.msg_fixes.append(msg)

        if pkg.get_version('grunt-stylelint') and pkg.get_version('stylelint') \
                and pkg.get_version('stylelint-config-wikimedia') \
                and library.is_greater_than_or_equal_to("0.5.0", pkg.get_version("stylelint-config-wikimedia")):
            pkg.remove_package('stylelint')
            changes = True
            self.msg_fixes.append('Remove direct "stylelint" dependency in favor of "grunt-stylelint".')

        if pkg.get_version('eslint-config-wikimedia'):
            for plugin in ['json', 'jsdoc', 'compat']:
                if pkg.get_version(f'eslint-plugin-{plugin}'):
                    pkg.remove_package(f'eslint-plugin-{plugin}')
                    changes = True
                    self.msg_fixes.append(f'Removed "eslint-plugin-{plugin}", already in "eslint-config-wikimedia".')

        if changes:
            pkg.save()
            # Regenerate package-lock.json super cleanly
            if os.path.exists('package-lock.json'):
                os.unlink('package-lock.json')
            if os.path.isdir('node_modules'):
                shutil.rmtree('node_modules')
            self.check_call(['npm', 'install'])
            self.check_package_lock()

    def fix_php_parallel_lint_migration(self):
        if not self.has_composer:
            return
        composer = ComposerJson('composer.json')
        migrate = {
            'jakub-onderka/php-parallel-lint': 'php-parallel-lint/php-parallel-lint',
            'jakub-onderka/php-console-highlighter': 'php-parallel-lint/php-console-highlighter',
        }
        changes = False
        for old, new in migrate.items():
            version = composer.get_version(old)
            if version is not None:
                composer.remove_package(old)
                composer.add_package(new, version)
                composer.save()
                changes = True

        if changes:
            self.msg_fixes.append(
                'Replaced "jakub-onderka" packages with '
                '"php-parallel-lint".')

    def fix_add_vendor_node_modules_to_gitignore(self, repo: str):
        """see T200620"""
        if repo in ('mediawiki/core', 'mediawiki/vendor'):
            # Don't mess with .gitignore, these repos are different
            return

        # TODO: Provde an abstraction for .gitignore
        if os.path.exists('.gitignore'):
            with open('.gitignore') as f:
                ignore = f.read()
        else:
            ignore = ''

        changes = False

        if self.has_composer:
            if 'vendor' not in ignore:
                ignore += '/vendor/\n'
                changes = True
                self.msg_fixes.append('.gitignore: Added vendor/ (T200620).')

            # Note: Not always-ignoring composer.lock, as it's used in mediawiki/vendor.git

        if self.has_npm:
            if 'node_modules' not in ignore:
                ignore += '/node_modules/\n'
                changes = True
                self.msg_fixes.append('.gitignore: Added node_modules/ (T200620).')

        if changes:
            with open('.gitignore', 'w') as f:
                f.write(ignore)

    def fix_phan_taint_check_plugin_merge_to_phan(self):
        if not self.has_composer:
            return

        composer = ComposerJson('composer.json')

        phanVersion = composer.get_version('mediawiki/mediawiki-phan-config')
        if (
            phanVersion is None or
            not library.is_greater_than_or_equal_to('0.10.0', phanVersion) or
            composer.get_extra('phan-taint-check-plugin') is None
        ):
            return

        composer.remove_extra('phan-taint-check-plugin')
        composer.save()
        self.msg_fixes.append('Removed phan-taint-check-plugin from extra, now inherited from mediawiki-phan-config.')

    def fix_phpunit_result_cache(self):
        if not self.has_composer:
            return

        composer = ComposerJson('composer.json')
        if composer.get_version('phpunit/phpunit') is None:
            return
        with open('.gitignore') as f:
            ignore = f.read()
        if '.phpunit.result.cache' in ignore:
            return
        ignore += '/.phpunit.result.cache\n'
        with open('.gitignore', 'w') as f:
            f.write(ignore)
        self.msg_fixes.append('.gitignore: Added .phpunit.result.cache (T242727).')

    def fix_composer_irc(self):
        if not self.has_composer:
            return

        data = load_ordered_json('composer.json')

        try:
            old = data['support']['irc']
        except KeyError:
            return

        if 'irc.freenode.net' not in old:
            return

        new = old.replace('irc.freenode.net', 'irc.libera.chat')

        data['support']['irc'] = new
        save_pretty_json(data, 'composer.json')
        self.msg_fixes.append('Updated composer IRC support URL to use Libera Chat (T283273)')

    def fix_stupid_npm_resolved(self):
        if not Path('package-lock.json').exists():
            return
        pkglock = load_ordered_json("package-lock.json")
        if pkglock['lockfileVersion'] != 1:
            return

        for name, dep in pkglock['dependencies'].items():
            self._recurse_dependencies(name, dep)
        save_pretty_json(pkglock, "package-lock.json")

    def _recurse_dependencies(self, name, dep):
        integrity = {
            "hosted-git-info": {
                "2.8.8": {
                    "version": "2.8.9",
                    "integrity": "sha512-mxIDAb9Lsm6DoOJ7xH+5+X4y1LU/4Hi50L9C5sIswK3JzULS4bwk1FvjdBgvYR4bzT4tuUQiC15FE2f5HbLvYw==",  # noqa
                },
                "3.0.7": {
                    "version": "3.0.8",
                    "integrity": "sha512-aXpmwoOhRBrw6X3j0h5RloK4x1OzsxMPyxqIHyNfSe2pypkVTZFpEiRoSipPEPlMrh0HW/XsjkJ5WgnCirpNUw==",  # noqa
                }
            },
            "lodash": {
                "4.17.20": {
                    "version": "4.17.21",
                    "integrity": "sha512-v2kDEe57lecTulaDIuNTPy3Ry4gLGJ6Z1O3vE1krgXZNrsQ+LFTGHVxVjcXPs17LhbZVGedAJv8XZ1tvj5FvSg==",  # noqa
                }
            },
            "ua-parser-js": {
                "0.7.21": {
                    "version": "0.7.21",
                    "integrity": "sha512-6Gurc1n//gjp9eQNXjD9O3M/sMwVtN5S8Lv9bvOYBfKfDNiIIhqiyi01vMBO45u4zkDE420w/e0se7Vs+sIg+g==",  # noqa
                }
            }
        }

        if "resolved" in dep:
            if dep["resolved"].startswith("http://registry.npmjs.org"):
                dep["resolved"] = dep["resolved"].replace("http://", "https://")
                msg = "Changed package-lock.json dependencies to use HTTPS"
                # Only add the msg fix once
                if msg not in self.msg_fixes:
                    self.msg_fixes.append(msg)

            try:
                info = integrity[name][dep['version']]
            except KeyError:
                info = None
            if info and dep["resolved"] == "":
                old_version = dep["version"]
                dep["version"] = info["version"]
                dep["resolved"] = f"https://registry.npmjs.org/{name}/-/{name}-{info['version']}.tgz"
                dep["integrity"] = info["integrity"]
                self.log_update(Update(manager="npm", name=name, old=old_version, new=info["version"]))
                self.weight += 10

        for name, subdep in dep.get("dependencies", {}).items():
            self._recurse_dependencies(name, subdep)

    def fix_phpcs_command(self):
        if not self.has_composer:
            return

        composer = ComposerJson('composer.json')
        if composer.get_version('mediawiki/mediawiki-codesniffer') is None:
            return

        changes = False
        j = composer.data

        phpcs_command = 'phpcs -sp --cache'

        for script in j['scripts']['test']:
            if script.startswith('phpcs'):
                pos = j['scripts']['test'].index(script)
                j['scripts']['test'].remove(script)
                j['scripts']['test'].insert(pos, '@phpcs')

                if script not in ['phpcs -p -s', 'phpcs -s -p', 'phpcs -ps', phpcs_command]:
                    phpcs_command = script

                self.msg_fixes.append('composer.json: Updated phpcs command in composer test (T280592).')
                changes = True
                break

        if 'phpcs' not in j['scripts']:
            j['scripts']['phpcs'] = phpcs_command
            self.msg_fixes.append('composer.json: Added phpcs command to scripts (T280592).')
            changes = True

        if changes:
            composer.data = j
            composer.save()

    def composer_upgrade(self, plan: list):
        if not self.has_composer:
            return
        prior = ComposerJson('composer.json')
        new = ComposerJson('composer.json')
        updates = []
        for manager, name, to, weight in plan:
            if manager != "composer":
                continue
            # Get the current version from composer.json
            current = prior.get_version(name)
            if current is None:
                # Might've been removed like eslint/stylelint (T242845)
                continue
            new.set_version(name, to)
            update = Update(
                'composer', name,
                current,
                to
            )
            self.log_update(update)
            updates.append(update)
            self.weight += weight

        new.save()
        if not updates:
            return
        self.check_call(['composer', 'update'])
        hooks = {
            'mediawiki/mediawiki-codesniffer': self._handle_codesniffer,
            'wikibase/wikibase-codesniffer': self._handle_codesniffer,
        }
        for update in updates:
            if update.name in hooks:
                # Pass the Update to the hook so
                # they can adjust reason, etc.
                hooks[update.name](update)

        # TODO: support rollback if this fails
        self.composer_test()

    def _handle_codesniffer(self, update: Update):
        if os.path.exists('.phpcs.xml'):
            phpcs_xml = '.phpcs.xml'
        else:
            phpcs_xml = 'phpcs.xml'
        if update.name == 'wikibase/wikibase-codesniffer':
            ref_name = 'vendor/wikibase/wikibase-codesniffer/Wikibase'
            find_rule = WB_FIND_RULE
            rule_no_exclude = WB_RULE_NO_EXCLUDE
            rule = WB_RULE
        else:
            ref_name = 'vendor/mediawiki/mediawiki-codesniffer/MediaWiki'
            find_rule = FIND_RULE
            rule_no_exclude = RULE_NO_EXCLUDE
            rule = RULE
        failing = set()
        now_failing = set()
        now_pass = set()

        with open(phpcs_xml, 'r') as f:
            old = f.read()

        tree = ElementTree.parse(phpcs_xml)
        root = tree.getroot()
        previously_failing = set()
        for child in root:
            if child.tag == 'rule' and ref_name in child.attrib.get('ref', ''):
                for grandchild in child:
                    if grandchild.tag == 'exclude':
                        previously_failing.add(grandchild.attrib['name'])
        self.log(str(previously_failing))

        # Re-enable all disabled rules
        with open(phpcs_xml, 'w') as f:
            new = find_rule.sub(
                '<rule ref="./' + ref_name + '" />',
                old
            )
            f.write(new)

        try:
            # TODO: use self.check_call
            subprocess.check_output(['vendor/bin/phpcs', '--report=json'])
        except subprocess.CalledProcessError as e:
            try:
                phpcs_j = json.loads(e.output.decode())
            except json.decoder.JSONDecodeError:
                self.log('Error, invalid JSON, skipping')
                self.log(e.output.decode())
                return False
            run_fix = False
            for fname, value in phpcs_j['files'].items():
                for message in value['messages']:
                    # Only run auto-fix on master
                    if message['fixable'] and self.is_main():
                        run_fix = True
                    else:
                        failing.add(message['source'])
            self.log('Tests fail!')
            if run_fix:
                try:
                    self.check_call(['vendor/bin/phpcbf'])
                except subprocess.CalledProcessError:
                    # phpcbf uses non-success error codes for other
                    # meanings. sigh.
                    pass
            for sniff in previously_failing:
                if sniff not in failing:
                    now_pass.add(sniff)
            for sniff in failing:
                if sniff not in previously_failing:
                    now_failing.add(sniff)
            self.check_call(['git', 'checkout', phpcs_xml])
            with open(phpcs_xml) as f:
                text = f.read()
            # Before we apply all of our regexes, let's get everything into a mostly standardized form
            # <exclude name="Foo"></exclude> -> <exclude name="Foo" />
            text = re.sub(
                r'<exclude name="(.*?)"></exclude>',
                r'<exclude name="\g<1>" />',
                text
            )
            for sniff in now_pass:
                text = re.sub(
                    '\t\t<exclude name="{}"( )?/>\n'.format(re.escape(sniff)),
                    '',
                    text
                )
            failing_list = list(sorted(failing))
            for i, sniff in enumerate(failing_list):
                if sniff in now_failing:
                    if i == 0:
                        # Expand self-closing rule tag
                        text = re.sub(
                            rule_no_exclude,
                            r'<rule \g<1>>\n\t</rule>',
                            text
                        )
                        text = text.replace(
                            rule,
                            rule + f'\n\t\t<exclude name="{sniff}" />'
                        )
                    else:
                        text = re.sub(
                            r'<exclude name="{}"( )?/>'.format(re.escape(failing_list[i - 1])),
                            '<exclude name="{}" />\n\t\t<exclude name="{}" />'.format(failing_list[i - 1], sniff),
                            text
                        )
            with open(phpcs_xml, 'w') as f:
                f.write(text)
            try:
                subprocess.check_call(['composer', 'test'])
            except subprocess.CalledProcessError:
                self.log('Tests still failing. Skipping')
                return False

        msg = ''
        if now_failing:
            msg += 'The following sniffs are failing and were disabled:\n'
            for sniff_name in sorted(now_failing):
                msg += '* ' + sniff_name + '\n'
            msg += '\n'

        if now_pass:
            msg += 'The following sniffs now pass and were enabled:\n'
            for sniff_name in sorted(now_pass):
                msg += '* ' + sniff_name + '\n'
            msg += '\n'
        update.reason = msg

    def npm_upgrade(self, plan: list):
        if not self.has_npm:
            return
        prior = PackageJson('package.json')
        new = PackageJson('package.json')
        updates = []
        for manager, name, to, weight in plan:
            if manager != "npm":
                continue
            # Get the current version from package.json
            current = prior.get_version(name)
            if current is None:
                # Might've been removed like eslint/stylelint (T242845)
                continue
            new.set_version(name, to)
            update = Update(
                'npm', name,
                current,
                to
            )
            self.log_update(update)
            updates.append(update)
            self.weight += weight

        new.save()
        if not updates:
            return
        self.check_call(['npm', 'install'])
        self.check_package_lock()
        hooks = {
            'eslint-config-wikimedia': [self._bump_eslint, self._handle_eslint],
            'stylelint-config-wikimedia': [self._handle_stylelint],
        }

        for update in updates:
            for hook in hooks.get(update.name, []):
                # Pass the Update to the hook so
                # they can adjust reason, etc.
                hook(update)

        # TODO: support rollback if this fails
        self.npm_test()

    def _bump_eslint(self, update: Update):
        grunt_eslint = PackageJson('package.json').get_version('grunt-eslint')
        if grunt_eslint:
            # Force re-install grunt-eslint to make eslint dedupe properly (T273680)
            self.check_call(['npm', 'install', f'grunt-eslint@{grunt_eslint}', '--save-exact'])
        self.check_package_lock()

    def _handle_stylelint(self, update: Update):
        pkg = PackageJson('package.json')
        if pkg.get_version('grunt-stylelint') and os.path.exists('Gruntfile.js'):
            try:
                self.check_call(['./node_modules/.bin/grunt', 'stylelint'])
                # Didn't fail, all good
                return
            except subprocess.CalledProcessError:
                pass
            # TODO: Support autofix once stylelint improves it
            gf = grunt.Gruntfile()
            try:
                files = grunt.expand_glob(gf.get_file_list('stylelint'))
            except:  # noqa
                # Some bug with the parser
                tb = traceback.format_exc()
                self.log(tb)
                return
        else:
            # If grunt isn't being used, lint all CSS/LESS files
            # https://phabricator.wikimedia.org/T248801#6031367
            files = grunt.expand_glob(['**/*.{css,less}'])

        errors = json.loads(self.check_call(['./node_modules/.bin/stylelint'] + files + [
            '-f', 'json'
        ], ignore_returncode=True))
        disable = set()
        for file in errors:
            for warning in file['warnings']:
                disable.add(warning['rule'])

        if disable:
            stylelint_cfg = load_ordered_json('.stylelintrc.json')
            msg = 'The following rules are failing and were disabled:\n'
            if 'rules' not in stylelint_cfg:
                stylelint_cfg['rules'] = OrderedDict()
            for rule in sorted(disable):
                stylelint_cfg['rules'][rule] = None
                msg += '* ' + rule + '\n'
            msg += '\n'

            if not stylelint_cfg['rules']:
                del stylelint_cfg['rules']
                self.msg_fixes.append('stylelint: Dropping empty `rules` definition.')

            save_pretty_json(stylelint_cfg, '.stylelintrc.json')
            update.reason = msg

    def _handle_eslint(self, update: Update):
        # eslint exits with status code of 1 if there are any
        # errors left, so ignore that. Just try and fix as much
        # as possible
        files = ['.']
        pkg = PackageJson('package.json')
        if pkg.get_version('grunt-eslint') and os.path.exists('Gruntfile.js'):
            gf = grunt.Gruntfile()
            try:
                files = grunt.expand_glob(gf.get_file_list('eslint'))
            except:  # noqa
                # Some bug with the parser
                tb = traceback.format_exc()
                self.log(tb)
                return

        if self.is_main():
            # Only run auto-fix on master
            self.check_call(['./node_modules/.bin/eslint'] + files + ['--fix'],
                            ignore_returncode=True)
        errors = json.loads(self.check_call([
            './node_modules/.bin/eslint'] + files + ['-f', 'json'], ignore_returncode=True))
        disable = set()
        to_undisable = defaultdict(set)
        for error in errors:
            fname = error['filePath']
            for message in error['messages']:
                if 'ruleId' not in message:
                    continue
                # eslint severity: 1 = warning, 2 = error.
                # We only care about errors.
                if message['ruleId'] and message['severity'] > 1:
                    disable.add(message['ruleId'])
                elif message['ruleId'] is None \
                        and 'Unused eslint-disable directive' in message['message']:
                    disable_match = ESLINT_DISABLE_RULE.search(message['message'])
                    if not disable_match:
                        # ???
                        self.log(f"Error: couldn't parse rule out of '{message['message']}'")
                        continue
                    disabled_rule = disable_match.group(1)
                    to_undisable[fname].add((message['line'], disabled_rule))

        for fname, disabled_rules in to_undisable.items():
            self.remove_eslint_disable(fname, disabled_rules)

        if disable:
            source, eslint_cfg = self._get_eslint_config()
            msg = 'The following rules are failing and were disabled:\n'

            if 'rules' not in eslint_cfg:
                eslint_cfg['rules'] = OrderedDict()
            for rule in sorted(disable):
                eslint_cfg['rules'][rule] = 'warn'
                msg += '* ' + rule + '\n'
            msg += '\n'

            if not eslint_cfg['rules']:
                del eslint_cfg['rules']
                self.msg_fixes.append('eslint: Dropping empty `rules` definition.')

            self._save_eslint_config(source, eslint_cfg)
            update.reason = msg

    def _get_eslint_config(self) -> Tuple[str, OrderedDict]:
        if Path(".eslintrc.json").exists():
            return ".eslintrc.json", load_ordered_json(".eslintrc.json")
        if Path("package.json").exists():
            pkg = load_ordered_json("package.json")
            if "eslintConfig" in pkg:
                return "package.json", pkg["eslintConfig"]
        raise RuntimeError("Cannot find eslint config")

    def _save_eslint_config(self, source: str, cfg: dict):
        if source == ".eslintrc.json":
            save_pretty_json(cfg, ".eslintrc.json")
        elif source == "package.json":
            pkg = load_ordered_json("package.json")
            pkg["eslintConfig"] = cfg
            save_pretty_json(pkg, "package.json")

    def remove_eslint_disable(self, fname: str, disabled_rules):
        with open(fname) as f:
            text = f.read()
        # Keep track of how many lines we delete
        offset = 0
        lines = text.splitlines()
        for lineno, rule in sorted(disabled_rules):
            idx = lineno - 1 - offset
            line = lines[idx]
            disable_line = ESLINT_DISABLE_LINE.search(line)
            if disable_line:
                rules_being_disabled = disable_line.group(2)
                if rules_being_disabled is None or rules_being_disabled.strip() == rule:
                    # easy peasy
                    newline = ESLINT_DISABLE_LINE.sub('', line).rstrip()
                elif ',' in rules_being_disabled:
                    sp = [x.strip() for x in rules_being_disabled.split(',')]
                    if rule not in sp:
                        # ??? it's not being disabled
                        return
                    sp.remove(rule)
                    newline = line.replace(rules_being_disabled, ' ' + ', '.join(sp))
                else:
                    # ???
                    return
                if newline.strip():
                    lines[idx] = newline
                else:
                    # If the line is empty now, get rid of it
                    del lines[idx]
                    offset += 1

        newtext = '\n'.join(lines)
        if newtext != text:
            count = len(disabled_rules)
            self.log(f'Removing eslint-disable-line (x{count}) from {fname}')
            if not newtext.endswith('\n'):
                newtext += '\n'
            with open(fname, 'w') as f:
                f.write(newtext)

    def commit(self, files: list, msg: str):
        f = tempfile.NamedTemporaryFile(delete=False)
        f.write(bytes(msg, 'utf-8'))
        f.close()
        self.check_call(['git', 'add'] + files)
        try:
            self.check_call(['git', 'commit', '-F', f.name])
        finally:
            os.unlink(f.name)

    def _indent(self, text, by=' '):
        new = []
        for line in text.splitlines():
            if line == '':
                new.append('')
            else:
                new.append(by + line)

        return '\n'.join(new)

    def build_message(self):
        if not self.updates:
            return '[DNM] there are no updates'
        if len(self.updates) == 1:
            update = self.updates[0]
            msg = f'build: Updating {update.name} to {update.new}\n'
            if update.reason:
                msg += '\n' + update.reason.strip() + '\n'
        else:
            by_manager = defaultdict(list)
            for update in self.updates:
                by_manager[update.manager].append(update)
            if len(list(by_manager)) == 1:
                msg = 'build: Updating %s dependencies\n\n' % self.updates[0].manager
                for update in self.updates:
                    msg += f'* {update.name}: {update.old} → {update.new}\n'
                    if update.reason:
                        msg += self._indent(update.reason, by='  ') + '\n'
            else:
                msg = 'build: Updating dependencies\n\n'
                for manager, updates in sorted(by_manager.items()):
                    msg += '%s:\n' % manager
                    for update in updates:
                        msg += f'* {update.name}: {update.old} → {update.new}\n'
                        if update.reason:
                            msg += self._indent(update.reason, by='  ') + '\n'
                    msg += '\n'

        if self.msg_fixes:
            msg += '\nAdditional changes:\n'
            for fix in self.msg_fixes:
                msg += '* %s\n' % fix

        return msg

    def get_hashtags(self) -> List[str]:
        hashtags = []
        for upd in self.updates:
            # We use a — instead of : or ; because those can't be used in git
            # commands apparently.
            hashtags.append('{}—{}={}'.format(upd.manager[0], upd.name, upd.new).replace('^', ''))
        hashtags.extend(list(self.cves))
        return hashtags

    def get_latest_patch(self):
        return self.check_call(['git', 'format-patch', 'HEAD~1', '--stdout'])

    def is_main(self):
        return self.git_branch in ("main", "master")

    def run(self, repo, output, branch):
        self.output = SaveDict({
            'repo': repo,
            'log': [],
        }, fname=output)
        self.git_branch = branch
        # Output the date we run as first thing
        self.check_call(['date'])
        self.clone(repo, internal=True, branch=self.git_branch)
        self.check_call(['grr', 'init'])  # Install commit-msg hook
        self.output['sha1'] = self.git_sha1(branch=self.git_branch)

        # Swap in the new php-parallel-lint package names
        self.fix_php_parallel_lint_migration()

        # Collect current dependencies
        self.output['npm-deps'] = self.npm_deps()
        self.output['composer-deps'] = self.composer_deps()

        # Fix the stupid npm resolved issue
        self.fix_stupid_npm_resolved()

        # audits
        self.output['audits'] = {
            'npm': self.npm_audit(),
            'composer': self.composer_audit(),
            'cargo': self.cargo_audit(),
        }

        # Now let's fix and upgrade stuff!

        # We need to do this first because it can cause problems
        # with later eslint/stylelint upgrades
        self.fix_remove_eslint_stylelint_if_grunt()
        # Also needs to be done early before we write to package-lock.json
        self.fix_package_json_metadata(repo)

        # Try upgrades
        planner = HTTPPlan(branch=self.git_branch)
        plan = planner.check(repo)
        self.npm_upgrade(plan)
        self.composer_upgrade(plan)

        # Re-run npm audit since upgrades might change stuff
        new_npm_audit = self.npm_audit()
        if new_npm_audit:
            self.npm_audit_fix(new_npm_audit)
        # TODO: composer audit

        self.output['push'] = self.weight >= WEIGHT_NEEDED \
            and bool(self.updates)

        # General fixes:
        self.fix_coc()
        self.fix_phpcs_xml_location()
        self.fix_phpcs_xml_configuration()
        self.fix_composer_fix()
        self.fix_composer_phan()
        self.fix_eslintrc_json_location()
        self.fix_stylelintrc_json_location()
        self.fix_root_eslintrc()
        self.fix_eslintrc_use_mediawiki_profile(repo)
        self.fix_eslint_config()
        self.fix_add_vendor_node_modules_to_gitignore(repo)
        self.fix_phpunit_result_cache()
        self.fix_phan_taint_check_plugin_merge_to_phan()
        self.fix_composer_irc()
        self.fix_phpcs_command()

        # Final check in case we missed something
        self.check_package_lock()

        # Commit
        msg = self.build_message()
        self.log(msg)
        try:
            self.commit(['.'], msg)
            self.output['patch'] = self.get_latest_patch()
        except subprocess.CalledProcessError:
            # git commit will exit 1 if there's nothing to commit
            self.output['patch'] = None
            self.output['push'] = False

        # Convert into a serializable form:
        self.output['hashtags'] = self.get_hashtags()
        # Deprecated
        self.output['updates'] = [upd.to_dict() for upd in self.updates]
        # Deprecated
        self.output['cves'] = list(self.cves)

        # Flag that we finished properly
        self.output['done'] = True


def main():
    parser = argparse.ArgumentParser(description='next generation of libraryupgrader')
    parser.add_argument('repo', help='Git repository')
    parser.add_argument('output', help='Path to output results to')
    parser.add_argument('--branch', help='Git branch', default='master')
    args = parser.parse_args()
    libup = LibraryUpgrader()
    try:
        libup.run(args.repo, args.output, args.branch)
    except:  # noqa
        # Make sure we log all exceptions that bubble up
        libup.log(traceback.format_exc())
        raise


if __name__ == '__main__':
    main()
