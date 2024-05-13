"""test_pycookiecheat.py :: Tests for pycookiecheat module."""

import os
import sys
import time
import typing as t
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.error import URLError
from uuid import uuid4

import pytest
from playwright.sync_api import sync_playwright

from pycookiecheat import BrowserType, chrome_cookies
from pycookiecheat.chrome import get_linux_config, get_macos_config

BROWSER = os.environ.get("TEST_BROWSER_NAME", "Chromium")


@pytest.fixture(scope="module")
def ci_setup() -> t.Generator:
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
        - Seems to require the "profile-directory" option instead of using the
          path to `Default` directly in user-data-dir
        - Seems to require a `max-age` for the cookie to last session to
          session

    https://chromium.googlesource.com/chromium/src/+/refs/heads/master/components/os_crypt/keychain_password_mac.mm
    """
    with TemporaryDirectory() as cookies_home, sync_playwright() as p:
        ex_path = os.environ.get("TEST_BROWSER_PATH")
        browser = p.chromium.launch_persistent_context(
            cookies_home,
            headless=False,
            chromium_sandbox=False,
            args=["--no-sandbox", "--disable-setuid-sandbox"],
            ignore_default_args=[
                "--use-mock-keychain",
            ],
            executable_path=ex_path,
        )
        page = browser.new_page()
        page.goto("https://n8henrie.com")
        browser.add_cookies(
            [
                {
                    "name": "test_pycookiecheat",
                    "value": "It worked!",
                    "domain": "n8henrie.com",
                    "path": "/",
                    "expires": int(time.time()) + 300,
                }
            ]
        )
        browser.close()
        cookie_file = Path(cookies_home) / "Default" / "Cookies"
        yield cookie_file


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


def test_warns_for_string_browser(ci_setup: str) -> None:
    """Browser should be passed as `BrowserType` and warns for strings."""
    never_been_here = "http://{0}.com".format(uuid4())
    with pytest.warns(
        DeprecationWarning,
        match=(
            "Please pass `browser` as a `BrowserType` " "instead of `str`."
        ),
    ):
        empty_dict = chrome_cookies(
            never_been_here,
            cookie_file=ci_setup,
            browser=BROWSER,  # type: ignore
        )
    assert empty_dict == dict()


def test_no_cookies(ci_setup: str) -> None:
    """Ensure that no cookies are returned for a fake url."""
    never_been_here = "http://{0}.com".format(uuid4())
    empty_dict = chrome_cookies(
        never_been_here,
        cookie_file=ci_setup,
        browser=BrowserType(BROWSER),
    )
    assert empty_dict == dict()


def test_fake_cookie(ci_setup: str) -> None:
    """Tests a fake cookie from the website below.

    For this to pass, you'll have to visit the url and put in "TestCookie" and
    "Just_a_test!" to set a temporary cookie with the appropriate values.
    """
    cookies = t.cast(
        dict,
        chrome_cookies(
            "https://n8henrie.com",
            cookie_file=ci_setup,
            browser=BrowserType(BROWSER),
        ),
    )
    assert cookies.get("test_pycookiecheat") == "It worked!"


def test_raises_on_wrong_browser() -> None:
    """Passing a browser other than Chrome or Chromium raises ValueError."""
    with pytest.raises(ValueError):
        BrowserType("edge")

    with pytest.raises(ValueError):
        chrome_cookies(
            "https://n8henrie.com",
            browser="Safari",  # type: ignore
        )


def test_slack_config() -> None:
    """Tests configuring for cookies from the macos Slack app.

    Hard to come up with a mock test, since the only functionality provided by
    the Slack app feature is to read cookies from a different file. So opt to
    just test that new functionality with something simple and fairly robust.
    """
    cfgs = []
    if sys.platform == "darwin":
        cfgs.append(get_macos_config(BrowserType.SLACK))

        parent = Path(
            "~/Library/Application Support/BraveSoftware/Brave-Browser/Default"
        )
        parent.mkdir(parents=True)
        (parent / "Cookies").touch()
        cfgs.append(get_macos_config(BrowserType.SLACK))

        assert cfgs[0] != cfgs[1]
    else:
        cfgs.append(get_linux_config(BrowserType.SLACK))

    for cfg in cfgs:
        assert "Slack" in str(cfg["cookie_file"])


def test_macos_bad_browser_variant() -> None:
    """Tests the error message resulting from unrecognized BrowserType."""
    for invalid in [BrowserType.FIREFOX, "foo"]:
        with pytest.raises(
            ValueError, match=f"{invalid} is not a valid BrowserType"
        ):
            get_macos_config(invalid)  # type: ignore
