import os
from setuptools import setup
from deflacue import VERSION


f = open(os.path.join(os.path.dirname(__file__), 'README.rst'))
README = f.read()
f.close()


setup(
    name='deflacue',
    version='.'.join(map(str, VERSION)),
    url='http://github.com/idlesign/deflacue',

    description='deflacue is a SoX based audio splitter to split audio CD images incorporated with .cue files',
    long_description=README,
    license='BSD 3-Clause License',

    author="Igor 'idle sign' Starikov",
    author_email='idlesign@yandex.ru',

    packages=['deflacue'],
    include_package_data=True,
    zip_safe=False,

    scripts=['bin/deflacue'],

    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: BSD License',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
        'Topic :: Multimedia :: Sound/Audio :: Conversion',
    ],
)
