#!/usr/bin/env python
from setuptools import setup

setup(name='etcd watcher',
      version='0.1',
      author='Santeri Paavolainen',
      author_email='santtu@iki.fi',
      install_requires=[
          'pyyaml',
          'python-etcd'
      ])
