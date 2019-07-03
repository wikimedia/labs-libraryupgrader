from setuptools import setup

setup(
    name='libup',
    version='0.0.1',
    packages=['libup'],
    url='https://www.mediawiki.org/wiki/Libraryupgrader',
    license='AGPL-3.0-or-later',
    author='Kunal Mehta',
    author_email='legoktm@member.fsf.org',
    description='semi-automated tool that manages upgrades of libraries',
    include_package_data=True,
    install_requires=[
        'requests',
        'wikimediaci-utils',
        # 'Flask',
        'flask-bootstrap',
        'gunicorn',
        'markdown',
        'semver',
        'celery',
    ],
    entry_points={
        'console_scripts': [
            'libup-run = libup.run:main',
            'libup-upgrade = libup.upgrade:main',
            'libup-ng = libup.ng:main',
        ]
    }

)
