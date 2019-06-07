#!/usr/bin/env python3
"""
Automatically updates library dependencies
Copyright (C) 2017-2018 Kunal Mehta <legoktm@member.fsf.org>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

# == NOTE ==
# This script runs *inside* a Docker container

from collections import OrderedDict
import json
import os
import re
import requests
import shutil
import subprocess
import tempfile
import urllib.parse
import xml.etree.ElementTree as ET

AUTO_APPROVE_FILES = {
    'composer.json',
    'package.json',
    'package-lock.json',
    'phpcs.xml',
    '.phpcs.xml',
    'phpcs.xml -> .phpcs.xml',
    'CODE_OF_CONDUCT.md',
}
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

s = requests.Session()


def gerrit_url(repo: str, user=None, pw=None) -> str:
    host = ''
    if user:
        if pw:
            host = user + ':' + urllib.parse.quote_plus(pw) + '@'
        else:
            host = user + '@'

    host += 'gerrit.wikimedia.org'
    return 'https://%s/r/%s.git' % (host, repo)


def commit_and_push(files, msg: str, branch: str, topic: str, remote='origin', plus2=False, push=True):
    f = tempfile.NamedTemporaryFile(delete=False)
    f.write(bytes(msg, 'utf-8'))
    f.close()
    subprocess.check_call(['git', 'add'] + files)
    subprocess.check_call(['git', 'commit', '-F', f.name])
    os.unlink(f.name)
    per = '%topic={0}'.format(topic)
    if plus2:
        per += ',l=Code-Review+2'
    push_cmd = ['git', 'push', remote,
                'HEAD:refs/for/{0}'.format(branch) + per]
    if push:
        try:
            subprocess.check_call(push_cmd)
        except subprocess.CalledProcessError:
            if plus2:
                # Try again without CR+2
                push_cmd[-1] = push_cmd[-1].replace(',l=Code-Review+2', '')
                subprocess.check_call(push_cmd)
            else:
                raise
    else:
        print(' '.join(push_cmd))


def rename_old_sniff_codes(phpcs_xml):
    with open(phpcs_xml, 'r') as f:
        old = f.read()
    with open(phpcs_xml, 'w') as f:
        new = old.replace(
            'MediaWiki.FunctionComment.Missing.Protected',
            'MediaWiki.Commenting.FunctionComment.MissingDocumentationProtected'
        ).replace(
            'MediaWiki.FunctionComment.Missing.Public',
            'MediaWiki.Commenting.FunctionComment.MissingDocumentationPublic'
        ).replace(
            'MediaWiki.WhiteSpace.OpeningKeywordBrace.WrongWhitespaceBeforeParenthesis',
            'MediaWiki.WhiteSpace.OpeningKeywordParenthesis.WrongWhitespaceBeforeParenthesis'
        ).replace(
            '<rule ref="vendor/mediawiki/mediawiki-codesniffer/MediaWiki">',
            RULE
        )
        new = re.sub(RULE_NO_EXCLUDE, RULE + '\n\t</rule>', new)
        f.write(new)


def update_coc():
    if not os.path.exists('CODE_OF_CONDUCT.md'):
        return ''

    with open('CODE_OF_CONDUCT.md') as f:
        old = f.read()
    new = old.replace(
        'https://www.mediawiki.org/wiki/Code_of_Conduct',
        'https://www.mediawiki.org/wiki/Special:MyLanguage/Code_of_Conduct'
    )
    if new == old:
        # No changes made
        return ''

    with open('CODE_OF_CONDUCT.md', 'w') as f:
        f.write(new)

    return 'And updating CoC link to use Special:MyLanguage (T202047).\n'


def npm_audit_fix():
    added_lock = False
    if not os.path.exists('package-lock.json'):
        added_lock = True
        subprocess.check_call(['npm', 'i', '--package-lock-only'])
        # We want to commit these now, so remove it from gitignore if it's in there
        if os.path.exists('.gitignore'):
            with open('.gitignore') as f:
                ignore = f.read()
            if 'package-lock.json' in ignore:
                ignore = re.sub(r'/?package-lock\.json\n', '', ignore)
                with open('.gitignore', 'w') as f:
                    f.write(ignore)
    try:
        subprocess.check_output(['npm', 'audit', '--json'])
        # If npm audit didn't fail, there are no vulnerable packages
        return False
    except subprocess.CalledProcessError as e:
        try:
            audit = json.loads(e.output.decode())
        except json.decoder.JSONDecodeError:
            print('Error, invalid JSON, skipping')
            print(e.output.decode())
            return False
    prior = PackageJson('package.json')
    subprocess.check_call(['npm', 'audit', 'fix', '--only=dev'])
    current = PackageJson('package.json')
    for pkg in current.get_packages():
        new_version = current.get_version(pkg)
        if new_version.startswith('^'):
            old_version = prior.get_version(pkg)
            if old_version and not old_version.startswith('^'):
                # If the old version didn't start with ^, then strip
                # it when npm audit fix adds it.
                current.set_version(pkg, new_version[1:])
                # If there's no old version / or the old version is valid, the new version
                # must be valid too
                if (not old_version or VALID_NPM_VERSION.match(old_version)) \
                        and not VALID_NPM_VERSION.match(current.get_version(pkg)):
                    print('Error: %s version is not valid: %s' % (pkg, current.get_version(pkg)))
                    return False
    current.save()

    # Verify that tests still pass
    subprocess.check_call(['npm', 'ci'])
    subprocess.check_call(['npm', 'test'])

    msg = 'build: Updating npm dependencies for security issues\n\n'
    for action in audit['actions']:
        if action['isMajor']:
            # We don't auto-update major versions
            continue
        msg += '* Updated %s to %s, addressing:\n' % (action['module'], action['target'])
        resolves = set(r['id'] for r in action['resolves'])
        for npm_id in sorted(resolves):
            msg += '  * https://npmjs.com/advisories/%s\n' % npm_id
            advisory_info = audit['advisories'][str(npm_id)]
            # TODO: line wrapping?
            if advisory_info.get('cves'):
                msg += '  * ' + ', '.join(advisory_info['cves']) + '\n'

    msg += '\n'
    if added_lock:
        msg += 'Committed package-lock.json (T179229) too.\n\n'

    return msg


def upgrade(env: dict):
    setup(env)
    # Whether auto approving is OK
    auto_ok = False
    if env['package'] == 'mediawiki/mediawiki-codesniffer':
        auto_ok = True
        success = update_codesniffer()
        if success is False:
            return False
    elif env['package'] == 'npm-audit-fix':
        auto_ok = True
        success = npm_audit_fix()
        if success is False:
            return False
    else:
        auto_ok = True
        success = update_package()

    part2 = update_coc()

    if env['package'] != 'npm-audit-fix':
        j = ComposerJson('composer.json')
        new_version = j.get_version(env['package'])

        msg = 'build: Updating %s to %s\n\n' % (env['package'], new_version)
    else:
        msg = ''

    if success:
        msg += success
    if part2:
        msg += part2
    print(msg)
    subprocess.call(['git', 'diff'])
    changed = subprocess.check_output(['git', 'status', '--porcelain']).decode().splitlines()
    changed_files = {x.strip().split(' ', 1)[1].strip() for x in changed}
    auto_approve = auto_ok and changed_files.issubset(AUTO_APPROVE_FILES)
    commit_and_push(
        files=['.'],
        msg=msg,
        branch='master',
        remote=gerrit_url(
            env['repo'],
            user=env['gerrit_user'],
            pw=env['gerrit_pw']
        ),
        topic='bump-dev-deps',
        plus2=auto_approve,
        push=True
    )


def update_package():
    subprocess.run(['composer', 'test'])
    return ''


class ComposerJson:
    def __init__(self, fname):
        self.fname = fname
        with open(fname, 'r') as f:
            self.data = json.load(f, object_pairs_hook=OrderedDict)

    def get_version(self, package):
        if package in self.data['require-dev']:
            return self.data['require-dev'][package]
        if 'extra' in self.data:
            suffix = package.split('/')[-1]
            if suffix in self.data['extra']:
                return self.data['extra'][suffix]

        return None

    def set_version(self, package, version):
        if package in self.data['require-dev']:
            self.data['require-dev'][package] = version
            return
        if 'extra' in self.data:
            suffix = package.split('/')[-1]
            if suffix in self.data['extra']:
                self.data['extra'][suffix] = version
                return

        raise RuntimeError('Unable to set version for %s to %s' % (package, version))

    def save(self):
        with open(self.fname, 'w') as f:
            out = json.dumps(self.data, indent='\t', ensure_ascii=False)
            f.write(out + '\n')


class PackageJson:
    def __init__(self, fname):
        self.fname = fname
        with open(fname, 'r') as f:
            self.data = json.load(f, object_pairs_hook=OrderedDict)

    def get_packages(self):
        return list(self.data['devDependencies'])

    def get_version(self, package):
        if package in self.data['devDependencies']:
            return self.data['devDependencies'][package]

        return None

    def set_version(self, package, version):
        if package in self.data['devDependencies']:
            self.data['devDependencies'][package] = version
            return

        raise RuntimeError('Unable to set version for %s to %s' % (package, version))

    def save(self):
        with open(self.fname, 'w') as f:
            out = json.dumps(self.data, indent='\t', ensure_ascii=False)
            f.write(out + '\n')


def update_codesniffer():
    composerjson = ComposerJson('composer.json')
    j = composerjson.data
    if os.path.exists('.phpcs.xml'):
        phpcs_xml = '.phpcs.xml'
    else:
        phpcs_xml = 'phpcs.xml'
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
    composerjson.data = j
    composerjson.save()

    moved_phpcs = False
    rename_old_sniff_codes(phpcs_xml)

    failing = set()
    now_failing = set()
    now_pass = set()

    with open(phpcs_xml, 'r') as f:
        old = f.read()

    tree = ET.parse(phpcs_xml)
    root = tree.getroot()
    previously_failing = set()
    for child in root:
        if child.tag == 'rule' and 'vendor/mediawiki/mediawiki-codesniffer/MediaWiki' in child.attrib.get('ref'):
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

    subprocess.call(['composer', 'update', '--prefer-dist'])

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
            subprocess.call(['composer', 'fix'])
        for sniff in previously_failing:
            if sniff not in failing:
                now_pass.add(sniff)
        for sniff in failing:
            if sniff not in previously_failing:
                now_failing.add(sniff)
        subprocess.check_call(['git', 'checkout', phpcs_xml])
        rename_old_sniff_codes(phpcs_xml)
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
        if phpcs_xml == 'phpcs.xml':
            subprocess.call(['git', 'mv', 'phpcs.xml', '.phpcs.xml'])
            moved_phpcs = True
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

    if moved_phpcs:
        msg += 'And moved phpcs.xml to .phpcs.xml (T177256).\n\n'

    if added_fix:
        msg += 'Also added phpcbf to "composer fix" command.'

    return msg


def build_env() -> dict:
    return {
        'repo': os.environ['REPO'],
        'version': os.environ.get('VERSION'),
        'package': os.environ['PACKAGE'],
        'gerrit_user': os.environ.get('GERRIT_USER'),
        'gerrit_pw': os.environ.get('GERRIT_PW')
    }


def setup(env: dict):
    gerrit = gerrit_url(env['repo'])
    subprocess.check_call(['git', 'clone', gerrit, 'repo', '--depth=1'])
    os.chdir('repo')
    subprocess.check_call(['grr', 'init'])  # Install commit-msg hook
    if env['version'] and env['version'] != 'none':
        j = ComposerJson('composer.json')
        j.set_version(env['package'], env['version'])
        j.save()
        subprocess.check_call(['composer', 'install'])


def test(env):
    setup(env)
    shutil.copy('/usr/src/myapp/phpcs.xml.sample', 'phpcs.xml')
    print('------------')
    # Don't use check_call since we expect this to fail
    out = subprocess.run(['vendor/bin/phpcs', '--report=json'], stdout=subprocess.PIPE)
    print(out.stdout.decode())
    print('------------')


def main():
    mode = os.environ['MODE']
    env = build_env()
    if mode == 'test':
        test(env)
    elif mode == 'upgrade':
        upgrade(env)
    else:
        raise ValueError('Unknown mode: ' + mode)


if __name__ == '__main__':
    main()
