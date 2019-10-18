#!/usr/bin/env python
"""A setuptools based setup module.

See:
https://packaging.python.org/en/latest/distributing.html
https://github.com/pypa/sampleproject
"""

# Always prefer setuptools over distutils
from setuptools import setup, find_packages
from os import path

here = path.abspath(path.dirname(__file__))

__author__ = 'Pepijn Mistiaen'
VERSION = '0.0.1'

setup(
    name='aioddwrt',
    version=VERSION,
    description='Api wrapper for DD-WRT https://dd-wrt.com',
    setup_requires=['setuptools-markdown',
                    'pytest-runner'],
    long_description_markdown_filename='README.md',
    url='https://github.com/lanquarden/aioddwrt',
    download_url='https://github.com/lanquarden/aioddrwrt/archive/%s.tar.gz' % VERSION,
    author=__author__,
    author_email='lanquarden@gmail.com',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
    ],
    keywords='ddwrt wrapper',
    packages=find_packages(exclude=['contrib', 'docs', 'tests']),
    install_requires=['asyncssh>=1.15.0', 'aiohttp'],
    test_suite='tests',
    tests_require=['pytest',
                   'pytest-cov',
                   'pytest-mock',
                   'pytest-asyncio'],
    extras_require={
        'dev': ['check-manifest'],
    },
)
