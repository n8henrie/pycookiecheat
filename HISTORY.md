# History

## 0.1.10

- Read version to separate file so it can be imported in setup.py
- Bugfix for python2 on linux

## 0.1.9

- Bugfix for python2 on linux

## 0.1.8

- Python2 support (thanks [dani14-96](https://github.com/dani14-96))

## 0.1.7

- Configurable cookies file (thanks [ankostis](https://github.com/ankostis))

## 0.1.6

- OSError instead of Exception for wrong OS.
- Moved testing requirements to tox and travis-ci files.

## 0.1.5

- Updated to work better with PyPI's lack of markdown support
- Working on tox and travis-ci integration
- Added a few basic tests that should pass if one has Chrome installed and has visited my site (n8henrie.com)
- Added sys.exit(0) if cookie_file not found so tests pass on travis-ci.

## 0.1.0 (2015-02-25)

- First release on PyPI.

## Prior changelog from Gist

- 20150221 v2.0.1: Now should find cookies for base domain and all subs.
- 20140518 v2.0: Now works with Chrome's new encrypted cookies.
