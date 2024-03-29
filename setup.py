from setuptools import setup

setup(
    name='libup',
    version='0.0.1',
    packages=['libup'],
    url='https://www.mediawiki.org/wiki/Libraryupgrader',
    license='AGPL-3.0-or-later',
    author='Kunal Mehta',
    author_email='legoktm@debian.org',
    description='semi-automated tool that manages upgrades of libraries',
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'libup-celery = libup.tasks:main',
            'libup-ng = libup.ng:main',
            'libup-run = libup.run:main',
        ]
    }

)
