# pycookiecheat

[![master branch build
status](https://github.com/n8henrie/pycookiecheat/actions/workflows/python-package.yml/badge.svg?branch=master)](https://github.com/n8henrie/pycookiecheat/actions/workflows/python-package.yml)

Borrow cookies from your browser's authenticated session for use in Python
scripts.

- Free software: MIT
- [Documentation](https://n8henrie.com/2013/11/use-chromes-cookies-for-easier-downloading-with-python-requests/)

## Installation

**NB:** Use `pip` and `python` instead of `pip3` and `python3` if you're still
on Python 2 and using pycookiecheat < v0.4.0. pycookiecheat >= v0.4.0 requires
Python 3 and in general will aim to support python versions that are stable and
not yet end-of-life: <https://devguide.python.org/versions>.

- `python3 -m pip install pycookiecheat`

### Installation notes regarding alternative keyrings on Linux

See [#12](https://github.com/n8henrie/pycookiecheat/issues/12). Chrome is now
using a few different keyrings to store your `Chrome Safe Storage` password,
instead of a hard-coded password. Pycookiecheat doesn't work with most of these
so far, and to be honest my enthusiasm for adding support for ones I don't use
is limited. However, users have contributed code that seems to work with some
of the recent Ubuntu desktops. To get it working, you may have to `sudo apt-get
install libsecret-1-dev python-gi python3-gi`, and if you're installing into a
virtualenv (highly recommended), you need to use the `--system-site-packages`
flag to get access to the necessary libraries.

Alternatively, some users have suggested running Chrome with the
`--password-store=basic` or `--use-mock-keychain` flags.

### Development Setup

1. `git clone https://github.com/n8henrie/pycookiecheat.git`
1. `cd pycookiecheat`
1. `python3 -m venv .venv`
1. `./.venv/bin/python -m pip install -e .[dev]`

## Usage

### As a Command-Line Tool

As of v0.7.0, pycookiecheat includes a command line tool for ease of use. By
default it prints the cookies to stdout as JSON but can also output a file in
Netscape Cookie File Format.

After installation, the CLI tool can be run as a python module `python -m` or
with a standalone console script:

```console
$ python -m pycookiecheat --help
usage: pycookiecheat [-h] [-b BROWSER] [-o OUTPUT_FILE] [-v] [-c COOKIE_FILE] [-V] url

Copy cookies from Chrome or Firefox and output as json

positional arguments:
  url                   requires scheme (e.g. `https://`)

options:
  -h, --help            show this help message and exit
  -b BROWSER, --browser BROWSER
  -o OUTPUT_FILE, --output-file OUTPUT_FILE
                        Output to this file in netscape cookie file format
  -v, --verbose         Increase logging verbosity (may repeat), default is `logging.ERROR`
  -c COOKIE_FILE, --cookie-file COOKIE_FILE
                        Cookie file
  -V, --version         show program's version number and exit```

### As a Python Library

```python
from pycookiecheat import BrowserType, chrome_cookies
import requests

url = 'https://n8henrie.com'

# Uses Chrome's default cookies filepath by default
cookies = chrome_cookies(url)
r = requests.get(url, cookies=cookies)

# Using an alternate browser
cookies = chrome_cookies(url, browser=BrowserType.CHROMIUM)
```

Use the `cookie_file` keyword-argument to specify a different filepath for the
cookies-file: `chrome_cookies(url, cookie_file='/abspath/to/cookies')`

You may be able to retrieve cookies for alternative Chromium-based browsers by
manually specifying something like
`"/home/username/.config/BrowserName/Default/Cookies"` as your `cookie_file`.

## Features

- Returns decrypted cookies from Google Chrome, Brave, or Slack, on MacOS or
  Linux.
- Optionally outputs cookies to file (thanks to Muntashir Al-Islam!)

## FAQ / Troubleshooting

### How about Windows?

I don't use Windows or have a PC, so I won't be adding support myself. Feel
free to make a PR :)

### I get an installation error with the `cryptography` module on OS X
(pycookiecheat <v0.4.0)

If you're getting [this
error](https://github.com/n8henrie/pycookiecheat/pull/11#issuecomment-221918807)
and using Homebrew, then you need to follow the instructions for [Building
cryptography on OS
X](https://cryptography.io/en/latest/installation/?highlight=cflags#building-cryptography-on-os-x)
and `export LDFLAGS="-L$(brew --prefix openssl)/lib" CFLAGS="-I$(brew --prefix
openssl)/include"` and try again.

### I get an installation error with the `cryptography` module on Linux

Please check the official cryptography docs. On some systems (e.g. Ubuntu), you
may need to do something like `sudo apt-get install build-essential libssl-dev
libffi-dev python-dev` prior to installing with `pip`.

### How can I use pycookiecheat on KDE-based Linux distros?

On KDE, Chrome defaults to using KDE's own keyring, KWallet. For pycookiecheat to support KWallet the [`dbus-python`](https://pypi.org/project/dbus-python/) package must be installed.

### How do I install the (unreleased) master branch with pip?

- `python -m pip install git+https://github.com/n8henrie/pycookiecheat@master`

## Buy Me a Coffee

[☕️](https://n8henrie.com/donate)
