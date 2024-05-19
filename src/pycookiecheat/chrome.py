"""pycookiecheat.py :: Retrieve and decrypt cookies from Chrome.

See relevant post at https://n8henrie.com/2013/11/use-chromes-cookies-for-easier-downloading-with-python-requests/  # noqa

Use your browser's cookies to make grabbing data from login-protected sites
easier. Intended for use with Python Requests http://python-requests.org

Accepts a URL from which it tries to extract a domain. If you want to force the
domain, just send it the domain you'd like to use instead.
"""

from __future__ import annotations

import logging
import sqlite3
import sys
import typing as t
import urllib.error
import urllib.parse
from pathlib import Path

import keyring
from cryptography.hazmat.primitives.ciphers import Cipher
from cryptography.hazmat.primitives.ciphers.algorithms import AES
from cryptography.hazmat.primitives.ciphers.modes import CBC
from cryptography.hazmat.primitives.hashes import SHA1
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from pycookiecheat.common import (
    BrowserType,
    Cookie,
    deprecation_warning,
    generate_host_keys,
    write_cookie_file,
)

logger = logging.getLogger(__name__)


def clean(decrypted: bytes) -> str:
    r"""Strip padding from decrypted value.

    Remove number indicated by padding
    e.g. if last is '\x0e' then ord('\x0e') == 14, so take off 14.

    Args:
        decrypted: decrypted value
    Returns:
        decrypted, stripped of padding
    """
    last = decrypted[-1]
    if isinstance(last, int):
        return decrypted[:-last].decode("utf8")

    try:
        cleaned = decrypted[: -ord(last)].decode("utf8")
    except UnicodeDecodeError:
        logging.error(
            "UTF8 decoding of the decrypted cookie failed. This is most often "
            "due to attempting decryption with an incorrect key. Consider "
            "searching the pycookiecheat issues for `UnicodeDecodeError`."
        )
        raise

    return cleaned


def chrome_decrypt(
    encrypted_value: bytes, key: bytes, init_vector: bytes
) -> str:
    """Decrypt Chrome/Chromium's encrypted cookies.

    Args:
        encrypted_value: Encrypted cookie from Chrome/Chromium's cookie file
        key: Key to decrypt encrypted_value
        init_vector: Initialization vector for decrypting encrypted_value
    Returns:
        Decrypted value of encrypted_value
    """
    # Encrypted cookies should be prefixed with 'v10' or 'v11' according to the
    # Chromium code. Strip it off.
    encrypted_value = encrypted_value[3:]

    cipher = Cipher(
        algorithm=AES(key),
        mode=CBC(init_vector),
    )
    decryptor = cipher.decryptor()
    decrypted = decryptor.update(encrypted_value) + decryptor.finalize()

    return clean(decrypted)


def get_macos_config(browser: BrowserType) -> dict:
    """Get settings for getting Chrome/Chromium cookies on MacOS.

    Args:
        browser: Enum variant representing browser of interest
    Returns:
        Config dictionary for Chrome/Chromium cookie decryption
    """
    app_support = Path("Library/Application Support")
    # TODO: Refactor to exhaustive match statement once depending on >= 3.10
    try:
        cookies_suffix = {
            BrowserType.CHROME: "Google/Chrome/Default/Cookies",
            BrowserType.CHROMIUM: "Chromium/Default/Cookies",
            BrowserType.BRAVE: "BraveSoftware/Brave-Browser/Default/Cookies",
            BrowserType.SLACK: "Slack/Cookies",
        }[browser]
    except KeyError as e:
        errmsg = (
            f"{browser} is not a valid BrowserType for {__name__}"
            ".get_macos_config"
        )
        raise ValueError(errmsg) from e
    cookie_file = "~" / app_support / cookies_suffix

    # Slack cookies can be in two places on MacOS depending on whether it was
    # installed from the App Store or direct download.
    if browser is BrowserType.SLACK and not cookie_file.exists():
        # And this location if Slack is installed from App Store
        cookie_file = (
            "~/Library/Containers/com.tinyspeck.slackmacgap/Data"
            / app_support
            / cookies_suffix
        )

    browser_name = browser.title()
    keyring_service_name = f"{browser_name} Safe Storage"

    keyring_username = browser_name
    if browser is BrowserType.SLACK:
        keyring_username = "Slack Key"

    key_material = keyring.get_password(keyring_service_name, keyring_username)
    if key_material is None:
        errmsg = (
            "Could not find a password for the pair "
            f"({keyring_service_name}, {keyring_username}). Please manually "
            "verify they exist in `Keychain Access.app`."
        )
        raise ValueError(errmsg)

    config = {
        "key_material": key_material,
        "iterations": 1003,
        "cookie_file": cookie_file,
    }
    return config


def get_linux_config(browser: BrowserType) -> dict:
    """Get the settings for Chrome/Chromium cookies on Linux.

    Args:
        browser: Enum variant representing browser of interest
    Returns:
        Config dictionary for Chrome/Chromium cookie decryption
    """
    cookie_file = (
        Path("~/.config")
        / {
            BrowserType.CHROME: "google-chrome/Default/Cookies",
            BrowserType.CHROMIUM: "chromium/Default/Cookies",
            BrowserType.BRAVE: "BraveSoftware/Brave-Browser/Default/Cookies",
            BrowserType.SLACK: "Slack/Cookies",
        }[browser]
    )

    # Set the default linux password
    config = {
        "key_material": "peanuts",
        "iterations": 1,
        "cookie_file": cookie_file,
    }

    browser_name = browser.title()

    # Try to get pass from Gnome / libsecret if it seems available
    # https://github.com/n8henrie/pycookiecheat/issues/12
    key_material = None
    try:
        import gi

        gi.require_version("Secret", "1")
        from gi.repository import Secret
    except ImportError:
        logger.info("Was not able to import `Secret` from `gi.repository`")
    else:
        flags = Secret.ServiceFlags.LOAD_COLLECTIONS
        service = Secret.Service.get_sync(flags)

        gnome_keyring = service.get_collections()
        unlocked_keyrings = service.unlock_sync(gnome_keyring).unlocked

        # While Slack on Linux has its own Cookies file, the password
        # is stored in a keyring named the same as Chromium's, but with
        # an "application" attribute of "Slack".
        keyring_name = f"{browser_name} Safe Storage"

        for unlocked_keyring in unlocked_keyrings:
            for item in unlocked_keyring.get_items():
                if item.get_label() == keyring_name:
                    item_app = item.get_attributes().get(
                        "application", browser
                    )
                    if item_app.lower() != browser.lower():
                        continue
                    item.load_secret_sync()
                    key_material = item.get_secret().get_text()
                    break
            else:
                # Inner loop didn't `break`, keep looking
                continue

            # Inner loop did `break`, so `break` outer loop
            break

    # Try to get pass from keyring, which should support KDE / KWallet
    # if dbus-python is installed.
    if key_material is None:
        try:
            key_material = keyring.get_password(
                f"{browser_name} Keys",
                f"{browser_name} Safe Storage",
            )
        except RuntimeError:
            logger.info("Was not able to access secrets from keyring")

    # Overwrite the default only if a different password has been found
    if key_material is not None:
        config["key_material"] = key_material

    return config


def chrome_cookies(
    url: str,
    cookie_file: t.Optional[t.Union[str, Path]] = None,
    browser: t.Optional[BrowserType] = BrowserType.CHROME,
    curl_cookie_file: t.Optional[t.Union[str, Path]] = None,
    password: t.Optional[t.Union[bytes, str]] = None,
    as_cookies: bool = False,
) -> t.Union[dict, list[Cookie]]:
    """Retrieve cookies from Chrome/Chromium on MacOS or Linux.

    Args:
        url: Domain from which to retrieve cookies, starting with http(s)
        cookie_file: Path to alternate file to search for cookies
        browser: Enum variant representing browser of interest
        curl_cookie_file: Path to save the cookie file to be used with cURL
        password: Optional system password
        as_cookies: Return `list[Cookie]` instead of `dict`
    Returns:
        Dictionary of cookie values for URL
    """
    parsed_url = urllib.parse.urlparse(url)
    if parsed_url.scheme:
        domain = parsed_url.netloc
    else:
        raise urllib.error.URLError("You must include a scheme with your URL.")

    # TODO: 20231229 remove str support after some deprecation period
    if not isinstance(browser, BrowserType):
        deprecation_warning(
            "Please pass `browser` as a `BrowserType` instead of "
            f"`{browser.__class__.__qualname__}`."
        )
        browser = BrowserType(browser)

    # If running Chrome on MacOS
    if sys.platform == "darwin":
        config = get_macos_config(browser)
    elif sys.platform.startswith("linux"):
        config = get_linux_config(browser)
    else:
        raise OSError("This script only works on MacOS or Linux.")

    config.update(
        {"init_vector": b" " * 16, "length": 16, "salt": b"saltysalt"}
    )

    if cookie_file is None:
        cookie_file = config["cookie_file"]
    cookie_file = Path(cookie_file)

    if isinstance(password, bytes):
        config["key_material"] = password
    elif isinstance(password, str):
        config["key_material"] = password.encode("utf8")
    elif isinstance(config["key_material"], str):
        config["key_material"] = config["key_material"].encode("utf8")

    kdf = PBKDF2HMAC(
        algorithm=SHA1(),
        iterations=config["iterations"],
        length=config["length"],
        salt=config["salt"],
    )
    enc_key = kdf.derive(config["key_material"])

    try:
        conn = sqlite3.connect(
            f"file:{cookie_file.expanduser()}?mode=ro", uri=True
        )
    except sqlite3.OperationalError as e:
        logger.error("Unable to connect to cookie_file at %s", cookie_file)
        raise e

    conn.row_factory = sqlite3.Row

    # Check whether the column name is `secure` or `is_secure`
    secure_column_name = "is_secure"
    for (
        sl_no,
        column_name,
        data_type,
        is_null,
        default_val,
        pk,
    ) in conn.execute("PRAGMA table_info(cookies)"):
        if column_name == "secure":
            secure_column_name = "secure AS is_secure"
            break

    sql = (
        "select host_key, path, "
        + secure_column_name
        + ", expires_utc, name, value, encrypted_value "
        "from cookies where host_key like ?"
    )

    cookies: list[Cookie] = []
    for host_key in generate_host_keys(domain):
        for db_row in conn.execute(sql, (host_key,)):
            # if there is a not encrypted value or if the encrypted value
            # doesn't start with the 'v1[01]' prefix, return v
            row = dict(db_row)
            if not row["value"] and (
                row["encrypted_value"][:3] in {b"v10", b"v11"}
            ):
                row["value"] = chrome_decrypt(
                    row["encrypted_value"],
                    key=enc_key,
                    init_vector=config["init_vector"],
                )
            del row["encrypted_value"]
            cookies.append(Cookie(**row))

    conn.rollback()

    if curl_cookie_file:
        write_cookie_file(curl_cookie_file, cookies)

    if as_cookies:
        return cookies

    return {c.name: c.value for c in cookies}
