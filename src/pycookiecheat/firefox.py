import configparser
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile
from typing import Dict
from typing import List
from typing import Optional
import urllib
import urllib.error
import urllib.parse

FIREFOX_COOKIE_SELECT_SQL = """
    SELECT name, value, `path`, isSecure, expiry
    FROM moz_cookies
    WHERE host = ?;
"""

FIREFOX_OS_PROFILE_DIRS: Dict[str, Dict[str, str]] = {
    "linux": {
        "Firefox": "~/.mozilla/firefox",
    },
    "osx": {
        "Firefox": "~/Library/Application Support/Firefox/Profiles",
    },
    "windows": {
        "Firefox": "~/AppData/Roaming/Mozilla/Firefox/Profiles",
    },
}


class FirefoxProfileNotPopulatedError(Exception):
    """Raised when the Firefox profile has never been used."""

    pass


def _get_profiles_dir_for_os(os: str, browser: str = "Firefox") -> Path:
    """Retrieve the default directory containing the user profiles."""
    browser = browser.title()
    try:
        os_config = FIREFOX_OS_PROFILE_DIRS[os]
    except KeyError:
        raise ValueError(
            f"OS must be one of {list(FIREFOX_OS_PROFILE_DIRS.keys())}"
        )
    try:
        return Path(os_config[browser]).expanduser()
    except KeyError:
        raise ValueError(f"Browser must be one of {list(os_config.keys())}")


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


def _copy_if_exists(src: List[Path], dest: Path):
    for file in src:
        try:
            shutil.copy2(file, dest)
        except FileNotFoundError:
            pass


def _load_firefox_cookie_db(
    profiles_dir: Path,
    tmp_dir: Path,
    profile_name: Optional[str] = None,
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
    profile_name: Optional[str] = None,
    browser: str = "Firefox",
    curl_cookie_file: Optional[str] = None,
) -> Dict[str, str]:
    """Retrieve cookies from Chrome/Chromium on OSX or Linux.

    Args:
        url: Domain from which to retrieve cookies, starting with http(s)
        profile_name: Name (or glob pattern) of the Firefox profile to search
                      for cookies -- if none given it will find the configured
                      default profile
        browser: Name of the browser's cookies to read (must be 'Firefox')
        curl_cookie_file: Path to save the cookie file to be used with cURL
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
        os = "osx"
    elif sys.platform == "win32":
        os = "windows"
    else:
        raise OSError(
            "This script only works on "
            + ", ".join(FIREFOX_OS_PROFILE_DIRS.keys())
        )
    profiles_dir = _get_profiles_dir_for_os(os, browser)

    cookies = {}
    curl_cookies = []
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_file = _load_firefox_cookie_db(
            profiles_dir, Path(tmp_dir), profile_name
        )
        with sqlite3.connect(db_file) as con:
            res = con.execute(FIREFOX_COOKIE_SELECT_SQL, (domain,))
            for key, value, path, is_secure, expiry in res.fetchall():
                cookies[key] = value
                if curl_cookie_file:
                    # http://www.cookiecentral.com/faq/#3.5
                    curl_cookies.append(
                        "\t".join(
                            [
                                domain,
                                "TRUE",
                                path,
                                "TRUE" if is_secure else "FALSE",
                                str(expiry),
                                key,
                                value,
                            ]
                        )
                    )
    if curl_cookie_file:
        with open(curl_cookie_file, "w") as text_file:
            text_file.write("\n".join(curl_cookies) + "\n")
    return cookies
