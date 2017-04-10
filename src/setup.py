#!/usr/bin/env python
# pylint: disable=relative-import,invalid-name
"""Setup file for appetite application"""
import os
from setuptools import setup, find_packages
import modules.version

PROJECT_ROOT = os.path.dirname(__file__)

with open('requirements.txt') as f:
    required = f.read().splitlines()

setup(name='appetite',
      version=modules.version.APPETITE_VERSION,
      description="Suite to install, manage and validate applications",
      author="XXXXXXXX",
      author_email='XXXXXXXXX@XXXXX.com',
      long_description=open(os.path.join(PROJECT_ROOT, '../README.md')).read(),
      install_requires=required,
      keywords='splunk, applications, install',
      packages=find_packages(),
      zip_safe=True,
      include_package_data=True,
      scripts=['appetite.py'],
      entry_points={
          'console_scripts': [
              'appetite=appetite:main'
          ]
      },
      test_suite="../tests")
