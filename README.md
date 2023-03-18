# pycookiecheat

[![master branch build
status](https://github.com/n8henrie/pycookiecheat/actions/workflows/python-package.yml/badge.svg?branch=master)](https://github.com/n8henrie/pycookiecheat/actions/workflows/python-package.yml)

Borrow cookies from your browser's authenticated session for use in Python
scripts.

-   Free software: MIT
-   Documentation: http://n8h.me/HufI1w

## Installation

**NB:** Use `pip` and `python` instead of `pip3` and `python3` if you're still
on Python 2 and using pycookiecheat < v0.4.0. pycookiecheat >= v0.4.0 requires
Python 3.5+, and may soon go to 3.6+.

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

```python
from pycookiecheat import chrome_cookies
import requests

url = 'http://example.com/fake.html'

# Uses Chrome's default cookies filepath by default
cookies = chrome_cookies(url)
r = requests.get(url, cookies=cookies)
```

Use the `cookie_file` keyword-argument to specify a different filepath for the
cookies-file: `chrome_cookies(url, cookie_file='/abspath/to/cookies')`

Keep in mind that pycookiecheat defaults to looking for cookies for
Chromium, not Google Chrome, so if you're using the latter, you'll need to
manually specify something like
`"/home/username/.config/google-chrome/Default/Cookies"` as your `cookie_file`.

## Features

- Returns decrypted cookies from Google Chrome on OSX or Linux.
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

### How do I install the dev branch with pip?

- `python -m pip install git+https://github.com/n8henrie/pycookiecheat@dev`

## Buy Me a Coffee

[☕️](https://n8henrie.com/donate)
