# -*- coding: utf-8 -*-

import re
from setuptools import setup, find_packages

try:
    import pypandoc
    readme = pypandoc.convert('README.md', 'rst')
    history = pypandoc.convert('HISTORY.md', 'rst')
except ImportError:
    with open('README.md') as readme_file:
        readme = readme_file.read()
    with open('HISTORY.md') as history_file:
        history = history_file.read()

version_regex = re.compile(r'__version__ = [\'\"]((\d+\.?)+)[\'\"]')
with open('src/pycookiecheat/__init__.py') as f:
    vlines = f.readlines()
__version__ = next(re.match(version_regex, line).group(1) for line in vlines
                   if re.match(version_regex, line))

with open('requirements.txt') as requirements_file:
    requirements = requirements_file.read().splitlines()

with open('requirements-dev.txt') as dev_requirements_file:
    dev_requirements = dev_requirements_file.read().splitlines()

setup(
    name='pycookiecheat',
    version=__version__,
    description="Borrow cookies from your browser's authenticated session for"
                "use in Python scripts.",
    long_description=readme + '\n\n' + history,
    author='Nathan Henrie',
    author_email='nate@n8henrie.com',
    url='https://github.com/n8henrie/pycookiecheat',
    packages=find_packages('src'),
    package_dir={"": "src"},
    include_package_data=True,
    install_requires=requirements,
    license="MIT",
    zip_safe=False,
    keywords='pycookiecheat chrome cookies',
    classifiers=[
        'Natural Language :: English',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],
    extras_require={
        "dev": dev_requirements
        },
    test_suite='tests',
    tests_require=['pytest==2.9.2']
)
