import re

from setuptools import find_packages, setup


def get_version(filename):
    with open(filename) as fh:
        metadata = dict(re.findall("__([a-z]+)__ = '([^']+)'", fh.read()))
        return metadata['version']


setup(
    name='Mopidy-Zestbox',
    version=get_version('mopidy_zestbox/__init__.py'),
    url='https://github.com/Andiscolemon/mopidy-zestbox',
    license='Apache License, Version 2.0',
    author='Andiscolemon',
    author_email='andiscolemon@gmail.com',
    description='A fork of Mopidy-Party, a web extension for Mopidy geared towards collaborative background listening.',
    long_description=open('README.rst').read(),
    packages=find_packages(exclude=['tests', 'tests.*']),
    zip_safe=False,
    include_package_data=True,
    install_requires=[
        'setuptools',
        'Mopidy >= 3.0',
        'Pykka >= 2.0.1',
    ],
    entry_points={
        'mopidy.ext': [
            'zestbox = mopidy_zestbox:Extension',
        ],
    },
    classifiers=[
        'Environment :: No Input/Output (Daemon)',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Topic :: Multimedia :: Sound/Audio :: Players',
    ],
)
