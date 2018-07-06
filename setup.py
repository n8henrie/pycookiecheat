import re

from setuptools import find_packages, setup

with open('README.md', encoding='utf8') as readme_file, \
        open('CHANGELOG.md', encoding='utf8') as history_file:
    readme = readme_file.read()
    history = history_file.read()

version_regex = re.compile(r'__version__ = [\'\"]v((\d+\.?)+)[\'\"]')
with open('src/pycookiecheat/__init__.py') as f:
    vlines = f.readlines()
__version__ = next(re.match(version_regex, line).group(1) for line in vlines
                   if re.match(version_regex, line))

with open('requirements.txt') as requirements_file:
    requirements = requirements_file.read().splitlines()

with open('requirements-dev.txt') as dev_requirements_file:
    dev_requirements = dev_requirements_file.read().splitlines()

with open("requirements-test.txt") as test_requirements_file:
    test_requirements = test_requirements_file.read().splitlines()
    dev_requirements.extend(test_requirements)

setup(
    name='pycookiecheat',
    version=__version__,
    description="Borrow cookies from your browser's authenticated session for"
                "use in Python scripts.",
    long_description=readme + '\n\n' + history,
    long_description_content_type='text/markdown',
    author='Nathan Henrie',
    author_email='nate@n8henrie.com',
    url='https://github.com/n8henrie/pycookiecheat',
    packages=find_packages("src"),
    package_dir={"": "src"},
    include_package_data=True,
    install_requires=requirements,
    license="MIT",
    zip_safe=False,
    keywords='pycookiecheat chrome cookies',
    classifiers=[
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    extras_require={
        "dev": dev_requirements
        },
    test_suite='tests',
    tests_require=test_requirements,
)
