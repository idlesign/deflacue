import io
import os
import re
import sys

from setuptools import setup

PATH_BASE = os.path.dirname(__file__)


def read_file(fpath):
    """Reads a file within package directories."""
    with io.open(os.path.join(PATH_BASE, fpath)) as f:
        return f.read()


def get_version():
    """Returns version number, without module import (which can lead to ImportError
    if some dependencies are unavailable before install."""
    contents = read_file(os.path.join('deflacue', '__init__.py'))
    version = re.search('VERSION = \(([^)]+)\)', contents)
    version = version.group(1).replace(', ', '.').strip()
    return version


setup(
    name='deflacue',
    version=get_version(),
    url='http://github.com/idlesign/deflacue',

    description='deflacue is a SoX based audio splitter to split audio CD images incorporated with .cue files',
    long_description=read_file('README.rst'),
    license='BSD 3-Clause License',

    author='Igor `idle sign` Starikov',
    author_email='idlesign@yandex.ru',

    packages=['deflacue'],
    include_package_data=True,
    zip_safe=False,

    setup_requires=[] + (['pytest-runner'] if 'test' in sys.argv else []) + [],

    entry_points={
        'console_scripts': ['deflacue = deflacue.cli:main'],
    },

    test_suite='tests',
    tests_require=[
        'pytest',
        'pytest-datafixtures',
    ],

    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: BSD License',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Topic :: Multimedia :: Sound/Audio :: Conversion',
    ],
)
