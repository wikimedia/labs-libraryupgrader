#!/usr/bin/env python3
"""
next generation of libraryupgrader

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

import argparse
from collections import defaultdict, OrderedDict
import json
import os
import re
import subprocess
import tempfile
import traceback
from typing import List
from xml.etree import ElementTree

from . import CANARIES, PHP_SECURITY_CHECK, gerrit, grunt, library, session, shell, utils
from .collections import SaveDict
from .data import Data
from .files import ComposerJson, PackageJson, PackageLockJson
from .update import Update

RULE = '<rule ref="./vendor/mediawiki/mediawiki-codesniffer/MediaWiki">'
RULE_NO_EXCLUDE = '<rule ref="(\./)?vendor/mediawiki/mediawiki-codesniffer/MediaWiki"( )?/>'
FIND_RULE = re.compile(
    '(' + re.escape(RULE) + '(.*?)' + re.escape('</rule>') +
    '|' + RULE_NO_EXCLUDE +
    ')',
    re.DOTALL
)
# Can have up to 2-4 number parts, and can't have any
# text like dev-master or -next
VALID_NPM_VERSION = re.compile('^(\d+?\.?){2,4}$')


class LibraryUpgrader(shell.ShellMixin):
    def __init__(self):
        self.msg_fixes = []
        self.updates = []  # type: List[Update]
        self.cves = set()
        self.is_canary = False
        self.output = None  # type: SaveDict

    def log(self, text: str):
        print(text)
        if self.output:
            self.output['log'].append(text)
            # FIXME: this shouldn't be needed
            self.output.save()

    def log_update(self, upd: Update):
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
        try:
            subprocess.check_output(['npm', 'audit', '--json'])
            # If npm audit didn't fail, there are no vulnerable packages
            return {}
        except subprocess.CalledProcessError as e:
            try:
                return json.loads(e.output.decode())
            except json.decoder.JSONDecodeError:
                self.log('Error, invalid JSON from npm audit, skipping')
                return {'error': e.output.decode()}

    def composer_audit(self):
        if not self.has_composer:
            return {}
        self.ensure_composer_lock()
        req = session.post(PHP_SECURITY_CHECK,
                           files={'lock': open('composer.lock', 'rb')},
                           headers={'Accept': 'application/json'})
        req.raise_for_status()
        return req.json()

    def npm_audit_fix(self, audit: dict):
        if not self.has_npm or not audit:
            return
        self.log('Attempting to npm audit fix')
        prior = PackageJson('package.json')
        prior_lock = PackageLockJson()
        self.check_call(['npm', 'audit', 'fix', '--only=dev'])
        current = PackageJson('package.json')
        for pkg in current.get_packages():
            new_version = current.get_version(pkg)
            old_version = prior.get_version(pkg)
            if new_version == old_version:
                # No change
                continue
            if new_version.startswith('^'):
                if old_version and not old_version.startswith('^'):
                    # If the old version didn't start with ^, then strip
                    # it when npm audit fix adds it.
                    current.set_version(pkg, new_version[1:])
                    # If there's no old version / or the old version is valid, the new version
                    # must be valid too
                    if (not old_version or VALID_NPM_VERSION.match(old_version)) \
                            and not VALID_NPM_VERSION.match(current.get_version(pkg)):
                        self.log('Error: %s version is not valid: %s' % (pkg, current.get_version(pkg)))
                        return

        current.save()

        # Verify that tests still pass
        self.log('Verifying that tests still pass')
        self.check_call(['npm', 'ci'])
        self.check_call(['npm', 'test'])

        for action in audit['actions']:
            if action.get('isMajor'):
                # We don't auto-update major versions
                continue
            if action['action'] != 'update':
                continue
            reason = ''
            resolves = set(r['id'] for r in action['resolves'])
            for npm_id in sorted(resolves):
                reason += '* https://npmjs.com/advisories/%s\n' % npm_id
                advisory_info = audit['advisories'][str(npm_id)]
                # TODO: line wrapping?
                if advisory_info.get('cves'):
                    reason += '* ' + ', '.join(advisory_info['cves']) + '\n'
                    self.cves.update(advisory_info['cves'])

            prior_version = prior.get_version(action['module'])
            if prior_version is None:
                # Try looking in the lockfile?
                prior_version = prior_lock.get_version(action['module'])
            upd = Update(
                'npm',
                action['module'],
                prior_version,
                action['target'],
                reason
            )
            self.log_update(upd)
            self.updates.append(upd)

    def npm_test(self):
        if not self.has_npm:
            return
        self.ensure_package_lock()
        self.check_call(['npm', 'ci'])
        self.check_call(['npm', 'test'])

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

    def fix_composer_fix(self):
        if not self.has_composer:
            return
        composerjson = ComposerJson('composer.json')
        if composerjson.get_version('mediawiki/mediawiki-codesniffer') is None:
            return
        j = composerjson.data
        added_fix = False
        if 'fix' in j['scripts']:
            if isinstance(j['scripts']['fix'], list):
                if 'phpcbf' not in j['scripts']['fix']:
                    j['scripts']['fix'].append('phpcbf')
                    added_fix = True
            elif j['scripts']['fix'] != 'phpcbf':
                j['scripts']['fix'] = [
                    j['scripts']['fix'],
                    'phpcbf'
                ]
                added_fix = True
        else:
            j['scripts']['fix'] = ['phpcbf']
            added_fix = True

        # TODO: resort "composer fix" so that phpcbf is last

        if added_fix:
            composerjson.data = j
            composerjson.save()
            self.msg_fixes.append('Also added phpcbf to "composer fix" command.')

    def fix_private_package_json(self, repo):
        if not repo.startswith(('mediawiki/extensions/', 'mediawiki/skins/')):
            # Only MW extensions and skins
            return
        if not self.has_npm:
            return
        pkg = PackageJson('package.json')
        if 'private' in pkg.data:
            return
        pkg.data['private'] = True
        # Move to top
        pkg.data.move_to_end('private', last=False)
        pkg.save()
        self.msg_fixes.append('Set `private: true` in package.json.')

    def fix_root_eslintrc(self):
        if not os.path.exists('.eslintrc.json'):
            return
        data = utils.load_ordered_json('.eslintrc.json')
        if 'root' in data:
            return
        data['root'] = True
        data.move_to_end('root', last=False)
        utils.save_pretty_json(data, '.eslintrc.json')
        self.msg_fixes.append('Set `root: true` in .eslintrc.json (T206485).')

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
            if '.eslintcache' not in gitignore:
                gitignore += '/.eslintcache\n'
            with open('.gitignore', 'w') as f:
                f.write(gitignore)
            if not set_options_cache:
                self.msg_fixes.append('Added .eslintcache to .gitignore.')
            changes = True
        pkg = PackageJson('package.json')
        eslint_cfg = pkg.get_version('eslint-config-wikimedia')
        if eslint_cfg and 'reportUnusedDisableDirectives' in data['options'] \
                and data['options']['reportUnusedDisableDirectives'] \
                and (eslint_cfg == '0.15.0' or library.is_greater_than('0.15.0', eslint_cfg)):
            del data['options']['reportUnusedDisableDirectives']
            self.msg_fixes.append('Removing manual reportUnusedDisableDirectives for eslint.')
            changes = True

        if changes:
            gf.set_section('eslint', data)
            gf.save()

    def sha1(self):
        return self.check_call(['git', 'show-ref', 'HEAD']).split(' ')[0]

    def composer_upgrade(self, info: dict):
        if not self.has_composer:
            return
        # TODO: support non-dev deps
        data = Data()
        deps = data.get_deps(info)['composer']['dev']
        prior = ComposerJson('composer.json')
        new = ComposerJson('composer.json')
        updates = []
        for lib in deps:
            if lib.is_newer() and lib.is_latest_safe() and \
                    (self.is_canary or data.check_canaries(lib.get_latest())):
                # Upgrade!
                new.set_version(lib.name, lib.latest_version())
                update = Update(
                    'composer', lib.name,
                    prior.get_version(lib.name),
                    lib.latest_version()
                )
                self.log_update(update)
                updates.append(update)
                self.updates.append(update)
        new.save()
        if not updates:
            return
        self.check_call(['composer', 'update'])
        hooks = {
            'mediawiki/mediawiki-codesniffer': self._handle_codesniffer,
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
        failing = set()
        now_failing = set()
        now_pass = set()

        with open(phpcs_xml, 'r') as f:
            old = f.read()

        tree = ElementTree.parse(phpcs_xml)
        root = tree.getroot()
        previously_failing = set()
        for child in root:
            if child.tag == 'rule' and child.attrib.get('ref') \
                    and 'vendor/mediawiki/mediawiki-codesniffer/MediaWiki' in child.attrib.get('ref'):
                for grandchild in child:
                    if grandchild.tag == 'exclude':
                        previously_failing.add(grandchild.attrib['name'])
        self.log(str(previously_failing))

        # Re-enable all disabled rules
        with open(phpcs_xml, 'w') as f:
            new = FIND_RULE.sub(
                '<rule ref="./vendor/mediawiki/mediawiki-codesniffer/MediaWiki" />',
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
                    if message['fixable']:
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
            # Before we apply all of our regexs, let's get everything into a mostly standardized form
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
            failing = list(sorted(failing))
            for i, sniff in enumerate(failing):
                if sniff in now_failing:
                    if i == 0:
                        text = text.replace(
                            RULE,
                            RULE + '\n\t\t<exclude name="{}" />'.format(sniff)
                        )
                    else:
                        text = re.sub(
                            r'<exclude name="{}"( )?/>'.format(re.escape(failing[i - 1])),
                            '<exclude name="{}" />\n\t\t<exclude name="{}" />'.format(failing[i - 1], sniff),
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

    def npm_upgrade(self, info: dict):
        if not self.has_npm:
            return
        # TODO: support non-dev deps
        data = Data()
        deps = data.get_deps(info)['npm']['dev']
        prior = PackageJson('package.json')
        new = PackageJson('package.json')
        updates = []
        for lib in deps:
            if lib.is_newer() and lib.is_latest_safe() and \
                    (self.is_canary or data.check_canaries(lib.get_latest())):
                # Upgrade!
                new.set_version(lib.name, lib.latest_version())
                update = Update(
                    'npm', lib.name,
                    prior.get_version(lib.name),
                    lib.latest_version()
                )
                self.log_update(update)
                updates.append(update)
                self.updates.append(update)
        new.save()
        if not updates:
            return
        self.check_call(['npm', 'install'])
        hooks = {
            'eslint-config-wikimedia': self._handle_eslint,
            'stylelint-config-wikimedia': self._handle_stylelint,
        }

        for update in updates:
            if update.name in hooks:
                # Pass the Update to the hook so
                # they can adjust reason, etc.
                hooks[update.name](update)

        # TODO: support rollback if this fails
        self.npm_test()

    def _handle_stylelint(self, update: Update):
        try:
            self.check_call(['./node_modules/.bin/grunt', 'stylelint'])
            # Didn't fail, all good
            return
        except subprocess.CalledProcessError:
            pass
        # TODO: Support autofix once stylelint improves it
        gf = grunt.Gruntfile()
        try:
            stylelint = gf.parse_section('stylelint')
        except grunt.NoSuchSection:
            # ???
            return
        except:  # noqa
            # Some bug with the parser
            tb = traceback.format_exc()
            self.log(tb)
            return
        # TODO: whaaaat. Why no consistency??
        gf_key = 'all' if 'all' in stylelint else 'src'
        files = grunt.expand_glob(stylelint[gf_key])
        errors = json.loads(self.check_call(['./node_modules/.bin/stylelint'] + files + [
            '-f', 'json'
        ], ignore_returncode=True))
        disable = set()
        for file in errors:
            for warning in file['warnings']:
                disable.add(warning['rule'])

        if disable:
            stylelint_cfg = utils.load_ordered_json('.stylelintrc.json')
            msg = 'The following rules are failing and were disabled:\n'
            if 'rules' not in stylelint_cfg:
                stylelint_cfg['rules'] = OrderedDict()
            for rule in sorted(disable):
                stylelint_cfg['rules'][rule] = None
                msg += '* ' + rule + '\n'
            msg += '\n'
            utils.save_pretty_json(stylelint_cfg, '.stylelintrc.json')
            update.reason = msg

    def _handle_eslint(self, update: Update):
        # eslint exits with status code of 1 if there are any
        # errors left, so ignore that. Just try and fix as much
        # as possible
        self.check_call(['./node_modules/.bin/eslint', '.', '--fix'],
                        ignore_returncode=True)
        errors = json.loads(self.check_call([
            './node_modules/.bin/eslint', '.', '-f', 'json'], ignore_returncode=True))
        disable = set()
        for error in errors:
            for message in error['messages']:
                if message['ruleId']:
                    disable.add(message['ruleId'])

        if disable:
            eslint_cfg = utils.load_ordered_json('.eslintrc.json')
            msg = 'The following rules are failing and were disabled:\n'

            if 'rules' not in eslint_cfg:
                eslint_cfg['rules'] = OrderedDict()
            for rule in sorted(disable):
                eslint_cfg['rules'][rule] = 'warn'
                msg += '* ' + rule + '\n'
            msg += '\n'
            utils.save_pretty_json(eslint_cfg, '.eslintrc.json')
            update.reason = msg

    def commit(self, files: list, msg: str):
        f = tempfile.NamedTemporaryFile(delete=False)
        f.write(bytes(msg, 'utf-8'))
        f.close()
        self.check_call(['git', 'add'] + files)
        self.check_call(['grr', 'init'])  # Install commit-msg hook
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
            msg = 'build: Updating %s to %s\n' % (update.name, update.new)
            if update.reason:
                msg += '\n' + update.reason.strip() + '\n'
        else:
            by_manager = defaultdict(list)
            for update in self.updates:
                by_manager[update.manager].append(update)
                if len(list(by_manager)) == 1:
                    msg = 'build: Updating %s dependencies\n\n' % self.updates[0].manager
                    for update in self.updates:
                        msg += '* %s: %s → %s\n' % (update.name, update.old, update.new)
                        if update.reason:
                            msg += self._indent(update.reason, by='  ') + '\n'
                else:
                    msg = 'build: Updating dependencies\n\n'
                    for manager, updates in sorted(by_manager.items()):
                        msg += '%s:\n' % manager
                        for update in updates:
                            msg += '* %s: %s → %s\n' % (update.name, update.old, update.new)
                            if update.reason:
                                msg += self._indent(update.reason, by='  ') + '\n'
                        msg += '\n'

        if self.msg_fixes:
            msg += '\nAdditional changes:\n'
            for fix in self.msg_fixes:
                msg += '* %s\n' % fix

        return msg

    def get_latest_patch(self):
        return self.check_call(['git', 'format-patch', 'HEAD~1', '--stdout'])

    def run(self, repo, output):
        self.output = SaveDict({
            'repo': repo,
            'log': [],
        }, fname=output)
        self.clone(repo)
        self.is_canary = repo in CANARIES
        self.output['sha1'] = self.sha1()

        # Collect current dependencies
        self.output['npm-deps'] = self.npm_deps()
        self.output['composer-deps'] = self.composer_deps()

        # Run tests
        self.log('Running tests to verify repository integrity')
        try:
            self.npm_test()
            self.output['npm-test'] = {'result': True}
        except subprocess.CalledProcessError as e:
            self.output['npm-test'] = {'result': False, 'error': e.output.decode()}
        try:
            self.composer_test()
            self.output['composer-test'] = {'result': True}
        except subprocess.CalledProcessError as e:
            self.output['composer-test'] = {'result': False, 'error': e.output.decode()}

        # npm audit
        self.output['npm-audit'] = self.npm_audit()
        self.output['composer-audit'] = self.composer_audit()

        self.output['open-changes'] = gerrit.query_changes(
            repo=repo, status='open', topic='bump-dev-deps'
        )

        # Do a pull to get the latest safe versions
        library.get_good_releases(pull=True)
        # Now let's fix and upgrade stuff!
        if self.output['npm-audit']:
            self.npm_audit_fix(self.output['npm-audit'])
        # TODO: composer audit

        # Try upgrades
        self.npm_upgrade(self.output)
        self.composer_upgrade(self.output)

        self.output['push'] = bool(self.updates) and not self.output['open-changes']

        # General fixes:
        self.fix_coc()
        self.fix_phpcs_xml_location()
        self.fix_composer_fix()
        self.fix_private_package_json(repo)
        self.fix_root_eslintrc()
        self.fix_eslint_config()

        # Commit
        msg = self.build_message()
        try:
            self.commit(['.'], msg)
            self.output['patch'] = self.get_latest_patch()
        except subprocess.CalledProcessError:
            # git commit will exit 1 if there's nothing to commit
            self.output['patch'] = None
            self.output['push'] = False

        # Convert into a serializable form:
        self.output['updates'] = [upd.to_dict() for upd in self.updates]
        self.output['cves'] = list(self.cves)

        # Flag that we finished properly
        self.output['done'] = True


def main():
    parser = argparse.ArgumentParser(description='next generation of libraryupgrader')
    parser.add_argument('repo', help='Git repository')
    parser.add_argument('output', help='Path to output results to')
    args = parser.parse_args()
    libup = LibraryUpgrader()
    try:
        libup.run(args.repo, args.output)
    except:  # noqa
        # Make sure we log all exceptions that bubble up
        libup.log(traceback.format_exc())
        raise


if __name__ == '__main__':
    main()
