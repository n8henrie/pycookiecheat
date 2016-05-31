# pycookiecheat

[![Build Status](https://travis-ci.org/n8henrie/pycookiecheat.svg?branch=master)](https://travis-ci.org/n8henrie/pycookiecheat)

Borrow cookies from your browser's authenticated session for use in Python scripts.

-   Free software: MIT
-   Documentation: http://n8h.me/HufI1w

## Installation
**NB:** Use `pip` and `python` instead of `pip3` and `python3` if you're still on Python 2.

### PyPI
- `pip3 install pycookiecheat`

### GitHub
1. `git clone https://github.com/n8henrie/pycookiecheat.git`
2. `cd pycookiecheat`
3. `python3 setup.py install`

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

## FAQ
### How about Windows?
I don't use Windows or have a PC, so I won't be adding support myself. Feel free to make a PR :)
