#!/usr/bin/env python
# Always prefer setuptools over distutils
from setuptools import setup, find_packages
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

setup(name='etcdwatch',
      version='0.3',
      description='Program to run a command whenever etcd registry changes',
      long_description=long_description,
      author='Santeri Paavolainen',
      author_email='santtu@iki.fi',
      license='MIT',
      url='https://github.com/santtu/etcdwatch',
      packages=find_packages(exclude=['tests']),
      classifiers=[
          'Development Status :: 3 - Alpha',
          'License :: OSI Approved :: MIT License',
          'Programming Language :: Python :: 2',
          'Programming Language :: Python :: 2.6',
          'Programming Language :: Python :: 2.7',
          'Programming Language :: Python :: 3',
          'Programming Language :: Python :: 3.4',
          'Programming Language :: Python :: 3.5'
      ],

      install_requires=[
          'pyyaml',
          'python-etcd'
      ],

      entry_points={
          'console_scripts': [
              'etcdwatch=etcdwatch:main',
          ],
      })
