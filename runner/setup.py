from setuptools import setup

setup(
    name='runner',
    version='0.1.0',
    packages=['runner'],
    url='https://www.mediawiki.org/wiki/Libraryupgrader',
    license='AGPL-3.0-or-later',
    author='Kunal Mehta',
    author_email='legoktm@debian.org',
    description='libup runner component',
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'runner = runner:main',
            'libup-ng = runner:main',
        ]
    }

)
