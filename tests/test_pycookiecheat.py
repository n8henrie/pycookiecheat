"""test_pycookiecheat.py :: Tests for pycookiecheat module."""

import sys
import typing as t
from pathlib import Path
from urllib.error import URLError
from uuid import uuid4

import pytest
from selenium import webdriver

from pycookiecheat import chrome_cookies


@pytest.fixture(scope="module")
def ci_setup() -> None:
    """Set up Chrome's cookies file and directory.

    Unfortunately, at least on MacOS 11, I haven't found a way to do this using
    a temporary directory or without accessing my actual keyring and profile.

    Things I've tried:
        - Use a temp directory for user-data-dir instead of actual Chrome
          profile
            - Seems not to work because the password is not correct for the
              profile.
            - Chrome generates a random password if one is not found for the
              profile, but this doesn't get added to Keychain and I haven't
              found a way to figure out what it's using for a particulary run

    Other notes:
        - Seems to require the "profile-directory" option instead of usign the
          path to `Default` directly in user-data-dir
        - Seems to require a `max-age` for the cookie to last session to
          session

    https://chromium.googlesource.com/chromium/src/+/refs/heads/master/components/os_crypt/keychain_password_mac.mm
    """
    cookies_home = {
        "darwin": "~/Library/Application Support/Google/Chrome",
        "linux": "~/.config/google-chrome",
    }[sys.platform]
    cookies_home = str(Path(cookies_home).expanduser())

    options = webdriver.chrome.options.Options()
    # options.add_argument("headless")
    options.add_argument("user-data-dir={}".format(cookies_home))
    options.add_argument("profile-directory=Default")
    options.add_experimental_option("excludeSwitches", ["use-mock-keychain"])

    driver = webdriver.Chrome(options=options)
    driver.get("https://n8henrie.com/")
    driver.add_cookie(
        {
            "name": "pycookiecheatTestCookie",
            "value": "Just_a_test!",
            "max-age": 60,
        }
    )
    driver.quit()


def test_raises_on_empty() -> None:
    """Ensure that `chrome_cookies()` raises."""
    with pytest.raises(TypeError):
        chrome_cookies()  # type: ignore


def test_raises_without_scheme() -> None:
    """Ensure that `chrome_cookies("domain.com")` raises.

    The domain must specify a scheme (http or https).

    """
    with pytest.raises(URLError):
        chrome_cookies("n8henrie.com")


def test_no_cookies(ci_setup: t.Callable) -> None:
    """Ensure that no cookies are returned for a fake url."""
    never_been_here = "http://{0}.com".format(uuid4())
    empty_dict = chrome_cookies(never_been_here)
    assert empty_dict == dict()


def test_fake_cookie(ci_setup: t.Callable) -> None:
    """Tests a fake cookie from the website below.

    For this to pass, you'll
    have to visit the url and put in "TestCookie" and "Just_a_test!" to set
    a temporary cookie with the appropriate values.

    """
    cookies = chrome_cookies(
        "https://n8henrie.com",
    )
    assert cookies["pycookiecheatTestCookie"] == "Just_a_test!"


def test_raises_on_wrong_browser() -> None:
    """Passing a browser other than Chrome or Chromium raises ValueError."""
    with pytest.raises(ValueError):
        chrome_cookies("https://n8henrie.com", browser="Safari")
