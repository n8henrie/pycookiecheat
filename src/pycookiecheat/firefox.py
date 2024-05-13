"""
Retrieve cookies from Firefox on various operating systems.

Returns a dict of cookie names & values.

Accepts a URL from which it tries to extract a domain. If you want to force the
domain, just send it the domain you'd like to use instead.

Example:
    >>> from pycookiecheat import firefox_cookies
    >>> firefox_cookies("https://github.com")
    {'logged_in': 'yes', 'user_session': 'n3tZzN45P56Ovg5MB'}
"""

from __future__ import annotations

import configparser
import logging
import shutil
import sqlite3
import sys
import tempfile
import typing as t
import urllib.error
import urllib.parse
from pathlib import Path

from pycookiecheat.common import (
    BrowserType,
    Cookie,
    deprecation_warning,
    generate_host_keys,
    write_cookie_file,
)

logger = logging.getLogger(__name__)

FIREFOX_COOKIE_SELECT_SQL = """
    SELECT
        `host` AS host_key,
        name,
        value,
        `path`,
        isSecure AS is_secure,
        expiry AS expires_utc
    FROM moz_cookies
    WHERE host = ?;
"""
"""
The query for selecting the cookies for a host.

Rename some columns to match the Chrome cookie db row names.
This makes the common.Cookie class simpler.
"""

FIREFOX_OS_PROFILE_DIRS: dict[str, dict[str, str]] = {
    "linux": {
        BrowserType.FIREFOX: "~/.mozilla/firefox",
    },
    "macos": {
        BrowserType.FIREFOX: "~/Library/Application Support/Firefox/Profiles",
    },
    "windows": {
        BrowserType.FIREFOX: "~/AppData/Roaming/Mozilla/Firefox/Profiles",
    },
}


class FirefoxProfileNotPopulatedError(Exception):
    """Raised when the Firefox profile has never been used."""

    pass


def _get_profiles_dir_for_os(
    os: str, browser: BrowserType = BrowserType.FIREFOX
) -> Path:
    """Retrieve the default directory containing the user profiles."""
    try:
        os_config = FIREFOX_OS_PROFILE_DIRS[os]
    except KeyError:
        raise ValueError(
            f"OS must be one of {list(FIREFOX_OS_PROFILE_DIRS.keys())}"
        )
    return Path(os_config[browser]).expanduser()


def _find_firefox_default_profile(firefox_dir: Path) -> str:
    """
    Return the name of the default Firefox profile.

    Args:
        firefox_dir: Path to the Firefox config directory
    Returns:
        Name of the default profile

    Firefox' profiles.ini file in the Firefox config directory that lists all
    available profiles.

    In Firefox versions 66 and below the default profile is simply marked with
    `Default=1` in the profile section. Firefox 67 started to support multiple
    installs of Firefox on the same machine and the default profile is now set
    in `Install...` sections. The install section contains the name of its
    default profile in the `Default` key.

    https://support.mozilla.org/en-US/kb/understanding-depth-profile-installation
    """
    profiles_ini = configparser.ConfigParser()
    profiles_ini.read(firefox_dir / "profiles.ini")
    installs = [s for s in profiles_ini.sections() if s.startswith("Install")]
    if installs:  # Firefox >= 67
        # Heuristic: Take the first install, that's probably the system install
        return profiles_ini[installs[0]]["Default"]
    else:  # Firefox < 67
        profiles = [
            s for s in profiles_ini.sections() if s.startswith("Profile")
        ]
        for profile in profiles:
            if profiles_ini[profile].get("Default") == "1":
                return profiles_ini[profile]["Path"]
        if profiles:
            return profiles_ini[profiles[0]]["Path"]
        raise Exception("no profiles found at {}".format(firefox_dir))


def _copy_if_exists(src: list[Path], dest: Path) -> None:
    for file in src:
        try:
            shutil.copy2(file, dest)
        except FileNotFoundError:
            pass


def _load_firefox_cookie_db(
    profiles_dir: Path,
    tmp_dir: Path,
    profile_name: t.Optional[str] = None,
) -> Path:
    """
    Return a file path to the selected browser profile's cookie database.

    Args:
        profiles_dir: Browser+OS paths profiles_dir path
        tmp_dir: A temporary directory to copy the DB file(s) into
        profile_name: Name (or glob pattern) of the Firefox profile to search
                      for cookies -- if none given it will find the configured
                      default profile
    Returns:
        Path to the "deWAL'ed" temporary copy of cookies.sqlite

    Firefox stores its cookies in an SQLite3 database file. While Firefox is
    running it has an exclusive lock on this file and other processes can't
    read from it. To circumvent this, copy the cookies file to the given
    temporary directory and read it from there.

    The SQLite database uses a feature called WAL ("write-ahead logging") that
    writes transactions for the database into a second file _prior_ to writing
    it to the actual DB. When copying the database this method also copies the
    WAL file and then merges any outstanding writes, to make sure the cookies
    DB has the most recent data.
    """
    if not profile_name:
        profile_name = _find_firefox_default_profile(profiles_dir)
    for profile_dir in profiles_dir.glob(profile_name):
        if (profile_dir / "cookies.sqlite").exists():
            break
    else:
        raise FirefoxProfileNotPopulatedError(profiles_dir / profile_name)
    cookies_db = profile_dir / "cookies.sqlite"
    cookies_wal = profile_dir / "cookies.sqlite-wal"
    _copy_if_exists([cookies_db, cookies_wal], tmp_dir)
    db_file = tmp_dir / "cookies.sqlite"
    if not db_file.exists():
        raise FileNotFoundError(f"no Firefox cookies DB in temp dir {tmp_dir}")
    with sqlite3.connect(db_file) as con:
        con.execute("PRAGMA journal_mode=OFF;")  # merge WAL
    return db_file


def firefox_cookies(
    url: str,
    profile_name: t.Optional[str] = None,
    browser: BrowserType = BrowserType.FIREFOX,
    curl_cookie_file: t.Optional[str] = None,
    as_cookies: bool = False,
) -> t.Union[dict, list[Cookie]]:
    """Retrieve cookies from Firefox on MacOS or Linux.

    Args:
        url: Domain from which to retrieve cookies, starting with http(s)
        profile_name: Name (or glob pattern) of the Firefox profile to search
                      for cookies -- if none given it will find the configured
                      default profile
        browser: Enum variant representing browser of interest
        curl_cookie_file: Path to save the cookie file to be used with cURL
        as_cookies: Return `list[Cookie]` instead of `dict`
    Returns:
        Dictionary of cookie values for URL
    """
    parsed_url = urllib.parse.urlparse(url)
    if parsed_url.scheme:
        domain = parsed_url.netloc
    else:
        raise urllib.error.URLError("You must include a scheme with your URL.")

    if sys.platform.startswith("linux"):
        os = "linux"
    elif sys.platform == "darwin":
        os = "macos"
    elif sys.platform == "win32":
        os = "windows"
    else:
        raise OSError(
            "This script only works on "
            + ", ".join(FIREFOX_OS_PROFILE_DIRS.keys())
        )

    # TODO: 20231229 remove str support after some deprecation period
    if not isinstance(browser, BrowserType):
        deprecation_warning(
            "Please pass `browser` as a `BrowserType` instead of "
            f"`{browser.__class__.__qualname__}`."
        )
        browser = BrowserType(browser)

    profiles_dir = _get_profiles_dir_for_os(os, browser)

    cookies: list[Cookie] = []
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_file = _load_firefox_cookie_db(
            profiles_dir, Path(tmp_dir), profile_name
        )
        for host_key in generate_host_keys(domain):
            with sqlite3.connect(db_file) as con:
                con.row_factory = sqlite3.Row
                res = con.execute(FIREFOX_COOKIE_SELECT_SQL, (host_key,))
                for row in res.fetchall():
                    cookies.append(Cookie(**row))

    if curl_cookie_file:
        write_cookie_file(curl_cookie_file, cookies)

    if as_cookies:
        return cookies

    return {c.name: c.value for c in cookies}
