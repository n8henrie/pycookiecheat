# -*- coding: utf-8 -*-
"""pyCookieCheat.py
See relevant post at http://n8h.me/HufI1w

Use your browser's cookies to make grabbing data from login-protected sites
easier. Intended for use with Python Requests http://python-requests.org

Accepts a URL from which it tries to extract a domain. If you want to force the
domain, just send it the domain you'd like to use instead.

Adapted from my code at http://n8h.me/HufI1w

"""

import sqlite3
import os.path
import keyring
import sys

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher
from cryptography.hazmat.primitives.ciphers.algorithms import AES
from cryptography.hazmat.primitives.ciphers.modes import CBC
from cryptography.hazmat.primitives.hashes import SHA1
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse


def chrome_cookies(url, cookie_file=None):

    salt = b'saltysalt'
    iv = b' ' * 16
    length = 16

    def chrome_decrypt(encrypted_value, key=None):

        # Encrypted cookies should be prefixed with 'v10' according to the
        # Chromium code. Strip it off.
        encrypted_value = encrypted_value[3:]

        # Strip padding by taking off number indicated by padding
        # eg if last is '\x0e' then ord('\x0e') == 14, so take off 14.
        def clean(x):
            last = x[-1]
            if isinstance(last, int):
                return x[:-last].decode('utf8')
            else:
                return x[:-ord(last)].decode('utf8')

        cipher = Cipher(
            algorithm=AES(key),
            mode=CBC(iv),
            backend=default_backend(),
        )
        decryptor = cipher.decryptor()
        decrypted = decryptor.update(encrypted_value) + decryptor.finalize()

        return clean(decrypted)

    # If running Chrome on OSX
    if sys.platform == 'darwin':
        my_pass = keyring.get_password('Chrome Safe Storage', 'Chrome')
        my_pass = my_pass.encode('utf8')
        iterations = 1003
        cookie_file = cookie_file or os.path.expanduser(
            '~/Library/Application Support/Google/Chrome/Default/Cookies'
        )

    # If running Chromium on Linux
    elif sys.platform.startswith('linux'):
        my_pass = 'peanuts'.encode('utf8')
        iterations = 1
        cookie_file = cookie_file or os.path.expanduser(
            '~/.config/chromium/Default/Cookies'
        )
    else:
        raise OSError("This script only works on OSX or Linux.")

    # Generate key from values above
    kdf = PBKDF2HMAC(
        algorithm=SHA1(),
        length=length,
        salt=salt,
        iterations=iterations,
        backend=default_backend(),
    )
    key = kdf.derive(bytes(my_pass))

    # Part of the domain name that will help the sqlite3 query pick it from the
    # Chrome cookies
    domain = urlparse(url).netloc

    conn = sqlite3.connect(cookie_file)

    sql = 'select name, value, encrypted_value from cookies where host_key '\
          'like ?'

    cookies = {}

    for host_key in generate_host_keys(domain):
        cookies_list = []
        for k, v, ev in conn.execute(sql, (host_key,)):
            # if there is a not encrypted value or if the encrypted value
            # doesn't start with the 'v10' prefix, return v
            if v or (ev[:3] != b'v10'):
                cookies_list.append((k, v))
            else:
                decrypted_tuple = (k, chrome_decrypt(ev, key=key))
                cookies_list.append(decrypted_tuple)
        cookies.update(cookies_list)

    conn.rollback()
    return cookies


def generate_host_keys(hostname):
    """Yield Chrome keys for `hostname`, from least to most specific.

    Given a hostname like foo.example.com, this yields the key sequence:

    example.com
    .example.com
    foo.example.com
    .foo.example.com

    """
    labels = hostname.split('.')
    for i in range(2, len(labels) + 1):
        domain = '.'.join(labels[-i:])
        yield domain
        yield '.' + domain
