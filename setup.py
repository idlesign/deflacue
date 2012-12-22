import os
from setuptools import setup
from deflacue import VERSION

f = open(os.path.join(os.path.dirname(__file__), 'README'))
readme = f.read()
f.close()

setup(
    name='deflacue',
    version=".".join(map(str, VERSION)),
    description='deflacue is a SoX based audio splitter to split audio CD images incorporated with .cue files',
    long_description=readme,
    author="Igor 'idle sign' Starikov",
    author_email='idlesign@yandex.ru',
    url='http://github.com/idlesign/deflacue',
    packages=['deflacue'],
    include_package_data=True,
    install_requires=['setuptools'],
    zip_safe=False,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: BSD License',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3.2',
        'Topic :: Multimedia :: Sound/Audio :: Conversion',
    ],
)
