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
from collections import defaultdict
import json
import os
import re
import subprocess
import tempfile
from typing import List
import urllib.parse
from xml.etree import ElementTree

from . import MANAGERS
from .data import Data
from .files import ComposerJson, PackageJson

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
AUTO_APPROVE_FILES = {
    'composer.json',
    'package.json',
    'package-lock.json',
    'phpcs.xml',
    '.phpcs.xml',
    'phpcs.xml -> .phpcs.xml',
    'CODE_OF_CONDUCT.md',
}


class Update:
    """dataclass representing an update"""
    def __init__(self, manager, name, old, new, reason=''):
        assert manager in MANAGERS
        self.manager = manager
        self.name = name
        self.old = old
        self.new = new
        self.reason = reason


class LibraryUpgrader:
    def __init__(self):
        self.logfile = None
        self.msg_fixes = []
        self.updates = []  # type: List[Update]
        self.security_fixes = False

    def log(self, text):
        if self.logfile:
            self.logfile.write(text)

    def finish(self):
        if self.logfile:
            self.logfile.close()

    def set_logfile(self, fname):
        self.logfile = open(fname, 'a')

    @property
    def has_npm(self):
        return os.path.exists('package.json')

    @property
    def has_composer(self):
        return os.path.exists('composer.json')

    def check_call(self, args: list) -> str:
        print('$ ' + ' '.join(args))
        res = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        # TODO: log
        print(res.stdout.decode())
        res.check_returncode()
        return res.stdout.decode()

    def gerrit_url(self, repo: str, user=None, pw=None) -> str:
        host = ''
        if user:
            if pw:
                host = user + ':' + urllib.parse.quote_plus(pw) + '@'
            else:
                host = user + '@'

        host += 'gerrit.wikimedia.org'
        return 'https://%s/r/%s.git' % (host, repo)

    def ensure_package_lock(self):
        if not os.path.exists('package-lock.json'):
            self.check_call(['npm', 'i', '--package-lock-only'])
            # We want to commit these now, so remove it from gitignore if it's in there
            if os.path.exists('.gitignore'):
                with open('.gitignore') as f:
                    ignore = f.read()
                if 'package-lock.json' in ignore:
                    ignore = re.sub(r'/?package-lock\.json\n', '', ignore)
                    with open('.gitignore', 'w') as f:
                        f.write(ignore)
            self.msg_fixes.append('Committed package-lock.json (T179229) too.')

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
                print('Error, invalid JSON from npm audit, skipping')
                return {'error': e.output.decode()}

    def npm_audit_fix(self, audit: dict):
        if not self.has_npm or not audit:
            return
        prior = PackageJson('package.json')
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
                        print('Error: %s version is not valid: %s' % (pkg, current.get_version(pkg)))
                        return

        current.save()

        # Verify that tests still pass
        self.check_call(['npm', 'ci'])
        self.check_call(['npm', 'test'])

        for action in audit['actions']:
            if action.get('isMajor'):
                # We don't auto-update major versions
                continue
            reason = ''
            resolves = set(r['id'] for r in action['resolves'])
            for npm_id in sorted(resolves):
                reason += '* https://npmjs.com/advisories/%s\n' % npm_id
                advisory_info = audit['advisories'][str(npm_id)]
                # TODO: line wrapping?
                if advisory_info.get('cves'):
                    reason += '* ' + ', '.join(advisory_info['cves']) + '\n'
            self.updates.append(Update(
                'npm',
                action['module'],
                prior.get_version(action['module']),
                action['target'],
                reason
            ))

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

    def clone_commands(self, repo):
        url = self.gerrit_url(repo)
        self.check_call(['git', 'clone', url, 'repo', '--depth=1'])
        os.chdir('repo')
        self.check_call(['grr', 'init'])  # Install commit-msg hook

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
                else:
                    pass
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

    def sha1(self):
        return self.check_call(['git', 'show-ref', 'HEAD']).split(' ')[0]

    def composer_upgrade(self, info: dict):
        if not self.has_composer:
            return
        # TODO: support non-dev deps
        deps = Data().get_deps(info)['composer']['dev']
        prior = ComposerJson('composer.json')
        new = ComposerJson('composer.json')
        updates = []
        for lib in deps:
            if lib.is_newer() and lib.is_latest_safe():
                # Upgrade!
                new.set_version(lib.name, lib.latest_version())
                update = Update(
                    'composer', lib.name,
                    prior.get_version(lib.name),
                    lib.latest_version()
                )
                updates.append(update)
                self.updates.append(update)
        new.save()
        self.check_call(['composer', 'update'])
        hooks = {
            'mediawiki/mediawiki-codesniffer': self._handle_codesniffer,
        }
        for update in updates:
            if update.name in hooks:
                # Pass the Update to the hook so
                # they can adjust reason, etc.
                hooks[update.name](update)

        try:
            self.composer_test()
        except subprocess.CalledProcessError:
            # TODO: log something somewhere?
            # rollback changes
            prior.save()

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
        print(previously_failing)

        # Re-enable all disabled rules
        with open(phpcs_xml, 'w') as f:
            new = FIND_RULE.sub(
                '<rule ref="./vendor/mediawiki/mediawiki-codesniffer/MediaWiki" />',
                old
            )
            f.write(new)

        try:
            subprocess.check_output(['vendor/bin/phpcs', '--report=json'])
        except subprocess.CalledProcessError as e:
            try:
                phpcs_j = json.loads(e.output.decode())
            except json.decoder.JSONDecodeError:
                print('Error, invalid JSON, skipping')
                print(e.output.decode())
                return False
            run_fix = False
            for fname, value in phpcs_j['files'].items():
                for message in value['messages']:
                    if message['fixable']:
                        run_fix = True
                    else:
                        failing.add(message['source'])
            print('Tests fail!')
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
            subprocess.check_call(['git', 'checkout', phpcs_xml])
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
                print('Tests still failing. Skipping')
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
        deps = Data().get_deps(info)['npm']['dev']
        prior = PackageJson('package.json')
        new = PackageJson('package.json')
        for lib in deps:
            if lib.is_newer() and lib.is_latest_safe():
                # Upgrade!
                new.set_version(lib.name, lib.latest_version())
                self.updates.append(Update(
                    'npm', lib.name,
                    prior.get_version(lib.name),
                    lib.latest_version()
                ))
        new.save()
        # TODO support upgrade hooks for e.g. eslint
        try:
            # Update lockfile
            self.check_call(['npm', 'install'])
            # Then test
            self.npm_test()
        except subprocess.CalledProcessError:
            # TODO: log something somewhere?
            # rollback changes
            prior.save()

    def commit_and_push(self, files: list, msg: str, branch: str,
                        topic: str, remote='origin', plus2=False, push=True):
        self.check_call(['git', 'diff'])
        f = tempfile.NamedTemporaryFile(delete=False)
        f.write(bytes(msg, 'utf-8'))
        f.close()
        self.check_call(['git', 'add'] + files)
        self.check_call(['git', 'commit', '-F', f.name])
        os.unlink(f.name)
        per = '%topic={0}'.format(topic)
        if plus2:
            per += ',l=Code-Review+2'
        push_cmd = ['git', 'push', remote,
                    'HEAD:refs/for/{0}'.format(branch) + per]
        if push:
            try:
                self.check_call(push_cmd)
            except subprocess.CalledProcessError:
                if plus2:
                    # Try again without CR+2
                    push_cmd[-1] = push_cmd[-1].replace(',l=Code-Review+2', '')
                    subprocess.check_call(push_cmd)
                else:
                    raise
        else:
            print(' '.join(push_cmd))

    def can_autoapprove(self) -> bool:
        changed = self.check_call(['git', 'status', '--porcelain']).splitlines()
        changed_files = {x.strip().split(' ', 1)[1].strip() for x in changed}
        return changed_files.issubset(AUTO_APPROVE_FILES)

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
            msg = 'build: Updating %s to %s' % (update.name, update.new)
            if update.reason:
                msg += '\n\n' + update.reason.strip() + '\n'
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
                    for manager, updates in by_manager.items():
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

    def run(self, repo, output):
        self.clone_commands(repo)
        data = {
            'repo': repo,
            'sha1': self.sha1()
        }

        # Collect current dependencies
        data['npm-deps'] = self.npm_deps()
        data['composer-deps'] = self.composer_deps()

        # Run tests
        try:
            self.npm_test()
            data['npm-test'] = {'result': True}
        except subprocess.CalledProcessError as e:
            data['npm-test'] = {'result': False, 'error': e.output.decode()}
        try:
            self.composer_test()
            data['composer-test'] = {'result': True}
        except subprocess.CalledProcessError as e:
            data['composer-test'] = {'result': False, 'error': e.output.decode()}

        # npm audit
        data['npm-audit'] = self.npm_audit()

        # Save all the data we collected.
        with open(output, 'w') as f:
            json.dump(data, f)

        # Now let's fix and upgrade stuff!
        if data['npm-audit']:
            self.npm_audit_fix(data['npm-audit'])
        # TODO: composer audit

        # Try upgrades
        self.npm_upgrade(data)
        self.composer_upgrade(data)

        # General fixes:
        self.fix_coc()
        self.fix_phpcs_xml_location()
        self.fix_composer_fix()

        # Commit
        can_autoapprove = self.can_autoapprove()
        msg = self.build_message()
        print(msg)
        self.commit_and_push(
            ['.'], msg, branch='master',
            topic='bump-dev-deps',
            plus2=can_autoapprove,
            push=False,  # TODO: enable pushing!
        )


def main():
    parser = argparse.ArgumentParser(description='next generation of libraryupgrader')
    parser.add_argument('repo', help='Git repository')
    parser.add_argument('output', help='Path to output results to')
    parser.add_argument('logfile', nargs='?', help='Log file')
    args = parser.parse_args()
    libup = LibraryUpgrader()
    if args.logfile:
        libup.set_logfile(args.logfile)
    try:
        libup.run(args.repo, args.output)
    finally:
        libup.finish()


if __name__ == '__main__':
    main()
