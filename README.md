# pycookiecheat

[![Build
Status](https://travis-ci.org/n8henrie/pycookiecheat.svg?branch=master)](https://travis-ci.org/n8henrie/pycookiecheat)

Borrow cookies from your browser's authenticated session for use in Python
scripts.

-   Free software: MIT
-   Documentation: http://n8h.me/HufI1w

## Installation

**NB:** Use `pip` and `python` instead of `pip3` and `python3` if you're still
on Python 2.

### Quickstart

- `pip3 install pycookiecheat`

### Development Setup

1. `git clone https://github.com/n8henrie/pycookiecheat.git`
1. `cd pycookiecheat`
1. `python3 -m venv venv`
1. `venv/bin/pip install -e .[dev]`

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

## Features

-  Returns decrypted cookies from Google Chrome on OSX or Linux.

## FAQ / Troubleshooting

### How about Windows?

I don't use Windows or have a PC, so I won't be adding support myself. Feel
free to make a PR :)

### I get an installation error with the `cryptography` module on OS X

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
