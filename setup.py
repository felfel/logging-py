# -*- coding: utf-8 -*-

from setuptools import setup, find_packages


setup(name='logging-py',
      version='0.3.15',
      url='https://github.com/felfel/logging-py',
      license='MIT License',
      author='felfel',
      author_email='tech@felfel.ch',
      description='Highly opinionated structured logging for python projects.',
      packages=find_packages(exclude=['examples', 'tests']),
      long_description=open('README.md').read(),
      zip_safe=False,)
