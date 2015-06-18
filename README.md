# pycookiecheat

Borrow cookies from your browser's authenticated session for use in Python scripts.

*   Free software: GPLv3
*   Documentation: http://n8h.me/HufI1w


## Installation

### PyPI
* `pip3 install pycookiecheat`

### GitHub
1. `git clone https://github.com/n8henrie/pycookiecheat.git`
2. `cd pycookiecheat`
3. `python3 setup.py install`

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

