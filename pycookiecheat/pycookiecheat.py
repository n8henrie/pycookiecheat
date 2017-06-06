"""pycookiecheat.py :: Retrieve and decrypt cookies from Chrome.

See relevant post at http://n8h.me/HufI1w

Use your browser's cookies to make grabbing data from login-protected sites
easier. Intended for use with Python Requests http://python-requests.org

Accepts a URL from which it tries to extract a domain. If you want to force the
domain, just send it the domain you'd like to use instead.

Adapted from my code at http://n8h.me/HufI1w

"""

import pathlib
import sqlite3
import sys
import urllib.error
import urllib.parse
from hashlib import pbkdf2_hmac
from typing import Any, Dict, Iterator, Union  # noqa

import keyring
from Crypto.Cipher import AES


def clean(decrypted: bytes) -> str:
    r"""Strip padding from decrypted value.

    Remove number indicated by padding
    e.g. if last is '\x0e' then ord('\x0e') == 14, so take off 14.

    Args:
        decrypted: decrypted value
    Returns:
        Decrypted stripped of junk padding

    """
    last = decrypted[-1]
    if isinstance(last, int):
        return decrypted[:-last].decode('utf8')
    return decrypted[:-ord(last)].decode('utf8')


def chrome_decrypt(encrypted_value: bytes, key: bytes, init_vector: bytes) \
        -> str:
    """Decrypt Chrome's encrypted cookies.

    Args:
        encrypted_value: Encrypted cookie value from Chrome's cookie file
        key: Key to decrypt encrypted_value
        init_vector: Initialization vector for decrypting encrypted_value
    Returns:
        Decrypted value of encrypted_value

    """
    # Encrypted cookies should be prefixed with 'v10' or 'v11' according to the
    # Chromium code. Strip it off.
    encrypted_value = encrypted_value[3:]

    cipher = AES.new(key, AES.MODE_CBC, IV=init_vector)
    decrypted = cipher.decrypt(encrypted_value)

    return clean(decrypted)


def get_osx_config() -> dict:
    """Get settings for getting Chrome cookies on OSX.

    Returns:
        Config dictionary for Chrome cookie decryption

    """
    config = {
        'my_pass': keyring.get_password('Chrome Safe Storage', 'Chrome'),
        'iterations': 1003,
        'cookie_file': ('~/Library/Application Support/Google/Chrome/Default/'
                        'Cookies'),
        }
    return config


def get_linux_config() -> dict:
    """Get the settings for Chrome cookies on Linux.

    Returns:
        Config dictionary for Chrome cookie decryption

    """
    # Set the default linux password
    config = {'my_pass': 'peanuts'}  # type: Dict[str, Union[int, str]]

    # Try to get from Gnome / libsecret if it seems available
    # https://github.com/n8henrie/pycookiecheat/issues/12
    try:
        import gi
        gi.require_version('Secret', '1')
        from gi.repository import Secret
    except ImportError:
        pass
    else:
        flags = Secret.ServiceFlags.LOAD_COLLECTIONS
        service = Secret.Service.get_sync(flags)

        gnome_keyring = service.get_collections()
        unlocked_keyrings = service.unlock_sync(gnome_keyring).unlocked

        for unlocked_keyring in unlocked_keyrings:
            for item in unlocked_keyring.get_items():
                if item.get_label() == "Chrome Safe Storage":
                    item.load_secret_sync()
                    config['my_pass'] = item.get_secret().get_text()
                    break
            else:
                # Inner loop didn't `break`, keep looking
                continue

            # Inner loop did `break`, so `break` outer loop
            break
    config.update({
        'iterations': 1,
        'cookie_file': '~/.config/chromium/Default/Cookies',
        })
    return config


def chrome_cookies(url: str, cookie_file: str = None) -> dict:
    """Retrieve cookies from Chrome or Chromium on OSX or Linux.

    Args:
        url: Domain from which to retrieve cookies, starting with http(s)
        cookie_file: Path to alternate file to search for cookies
    Returns:
        Dictionary of cookie values for URL

    """
    # If running Chrome on OSX
    if sys.platform == 'darwin':
        config = get_osx_config()

    elif sys.platform.startswith('linux'):
        config = get_linux_config()
    else:
        raise OSError("This script only works on OSX or Linux.")

    config.update({
        'init_vector': b' ' * 16,
        'length': 16,
        'salt': b'saltysalt',
    })

    if cookie_file:
        cookie_file = str(pathlib.Path(cookie_file).expanduser())
    else:
        cookie_file = str(pathlib.Path(config['cookie_file']).expanduser())

    # https://github.com/python/typeshed/pull/1241
    enc_key = pbkdf2_hmac(hash_name='sha1',  # type: ignore
                          password=config['my_pass'].encode('utf8'),
                          salt=config['salt'],
                          iterations=config['iterations'],
                          dklen=config['length'])

    parsed_url = urllib.parse.urlparse(url)
    if parsed_url.scheme:
        domain = parsed_url.netloc
    else:
        raise urllib.error.URLError("You must include a scheme with your URL.")

    conn = sqlite3.connect(cookie_file)

    sql = ('select name, value, encrypted_value from cookies where host_key '
           'like ?')

    cookies = dict()

    for host_key in generate_host_keys(domain):
        for cookie_key, val, enc_val in conn.execute(sql, (host_key,)):
            # if there is a not encrypted value or if the encrypted value
            # doesn't start with the 'v1[01]' prefix, return v
            if val or (enc_val[:3] not in (b'v10', b'v11')):
                pass
            else:
                val = chrome_decrypt(enc_val, key=enc_key,
                                     init_vector=config['init_vector'])
            cookies[cookie_key] = val

    conn.rollback()
    return cookies


def generate_host_keys(hostname: str) -> Iterator[str]:
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
