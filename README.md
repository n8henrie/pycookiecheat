# pycookiecheat

Borrow cookies from your browser's authenticated session for use in Python scripts.

*   Free software: GPLv3
*   Documentation: http://n8h.me/HufI1w


## Installation

### PyPI
* Unsupported (yet)

### GitHub
1. `git clone -b python2 https://github.com/dani14-96/pycookiecheat.git` (change user after PR)
2. `cd pycookiecheat`
3. `python setup.py install`


## Usage
```python
from pycookiecheat import chrome_cookies
import requests

url = 'http://example.com/fake.html'

cookies = chrome_cookies(url) ## Platform's default filepath.
r = requests.get(url, cookies=cookies)
```

Use the `cookie_file` keyword-argument to specify a different filepath for the
cookies-file: `chrome_cookies(url, cookie_file=/abspath/to/cookies)`

## Features
*  Returns decrypted cookies from Google Chrome on OSX or Linux.

## FAQ
### How about Windows?
I don't use Windows or have a PC, so I won't be adding support myself. Feel free to make a PR :)
