"""Tests for Firefox cookies & helper functions."""

import re
import typing as t
from datetime import datetime, timedelta
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from textwrap import dedent
from threading import Thread
from unittest.mock import patch
from urllib.error import URLError

import pytest
from playwright.sync_api import sync_playwright
from pytest import FixtureRequest, TempPathFactory

from pycookiecheat import BrowserType, firefox_cookies
from pycookiecheat.firefox import (
    _find_firefox_default_profile,
    _get_profiles_dir_for_os,
    _load_firefox_cookie_db,
    FirefoxProfileNotPopulatedError,
)

TEST_PROFILE_NAME = "test-profile"
TEST_PROFILE_DIR = f"1234abcd.{TEST_PROFILE_NAME}"

PROFILES_INI_VERSION1 = dedent(
    f"""
    [General]
    StartWithLastProfile=1

    [Profile0]
    Name={TEST_PROFILE_NAME}
    IsRelative=1
    Path={TEST_PROFILE_DIR}
    Default=1

    [Profile1]
    Name={TEST_PROFILE_NAME}2
    IsRelative=1
    Path=abcdef01.{TEST_PROFILE_NAME}2
    """
)

PROFILES_INI_VERSION2 = dedent(
    f"""
    [Install8149948BEF895A0D]
    Default={TEST_PROFILE_DIR}
    Locked=1

    [General]
    StartWithLastProfile=1
    Version=2

    [Profile0]
    Name={TEST_PROFILE_NAME}
    IsRelative=1
    Path={TEST_PROFILE_DIR}
    Default=1
    """
)

PROFILES_INI_EMPTY = dedent(
    """
    [General]
    StartWithLastProfile=1
    Version=2
    """
)

PROFILES_INI_VERSION1_NO_DEFAULT = dedent(
    f"""
    [General]
    StartWithLastProfile=1
    Version=2

    [Profile0]
    Name={TEST_PROFILE_NAME}
    IsRelative=1
    Path={TEST_PROFILE_DIR}
    """
)

PROFILES_INI_VERSION2_NO_DEFAULT = dedent(
    f"""
    [Install8149948BEF895A0D]
    Default={TEST_PROFILE_DIR}
    Locked=1

    [General]
    StartWithLastProfile=1
    Version=2

    [Profile0]
    Name={TEST_PROFILE_NAME}
    IsRelative=1
    Path={TEST_PROFILE_DIR}
    """
)


def _make_test_profiles(
    tmp_path: Path, profiles_ini_content: str, populate: bool = True
) -> t.Iterator[Path]:
    """Create a Firefox data dir with profile & (optionally) populate it.

    All of the fixtures using this function use the pytest builtin `tmp_path`
    or `tmp_path_factory` fixtures to create their temporary directories.
    """
    profile_dir = tmp_path / TEST_PROFILE_DIR
    profile_dir.mkdir()
    (tmp_path / "profiles.ini").write_text(profiles_ini_content)
    if populate:
        with sync_playwright() as p:
            p.firefox.launch_persistent_context(
                user_data_dir=profile_dir,
                headless=True,
            ).close()
    with patch(
        "pycookiecheat.firefox._get_profiles_dir_for_os",
        return_value=tmp_path,
    ):
        yield tmp_path


@pytest.fixture(scope="module")
def profiles(tmp_path_factory: TempPathFactory) -> t.Iterator[Path]:
    """Create a Firefox data dir with profiles & cookie DBs."""
    yield from _make_test_profiles(
        tmp_path_factory.mktemp("_"), PROFILES_INI_VERSION2
    )


@pytest.fixture(
    scope="module",
    params=[
        PROFILES_INI_VERSION1,
        PROFILES_INI_VERSION2,
        PROFILES_INI_VERSION1_NO_DEFAULT,
        PROFILES_INI_VERSION2_NO_DEFAULT,
    ],
)
def profiles_ini_versions(
    tmp_path_factory: TempPathFactory, request: FixtureRequest
) -> t.Iterator[Path]:
    """Create a Firefox data dir using varius `profiles.ini` types.

    Use different file format versions and contents.
    """
    yield from _make_test_profiles(tmp_path_factory.mktemp("_"), request.param)


@pytest.fixture(scope="module")
def no_profiles(tmp_path_factory: TempPathFactory) -> t.Iterator[Path]:
    """Create a Firefox data dir with a `profiles.ini` with no profiles."""
    yield from _make_test_profiles(
        tmp_path_factory.mktemp("_"), PROFILES_INI_EMPTY
    )


# TODO: Making this fixture module-scoped breaks the tests using the `profiles`
#       fixture. Find out why.
@pytest.fixture
def profiles_unpopulated(tmp_path: Path) -> t.Iterator[Path]:
    """Create a Firefox data dir with valid but upopulated `profiles.ini` file.

    "Unpopulated" means never actually used to launch Firefox with.
    """
    yield from _make_test_profiles(
        tmp_path, PROFILES_INI_VERSION2, populate=False
    )


@pytest.fixture(scope="session")
def cookie_server() -> t.Iterator[int]:
    """Start an `HTTPServer` on localhost which sets a cookie.

    Replies to GET requests by setting a "foo: bar" cookie.
    Used as fixture for testing cookie retrieval.

    Returns:
        The port of the server on localhost.
    """

    class CookieSetter(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802, must be named with HTTP verb
            self.send_response(200)
            cookie: SimpleCookie = SimpleCookie()
            cookie["foo"] = "bar"
            cookie["foo"]["path"] = "/"
            # Needs an expiry time, otherwise it's a session cookie, which are
            # never saved to disk. (Well, _technically_ they sometimes are,
            # when the browser is set to resume the session on restart, but we
            # aren't concerned with that here.)
            this_time_tomorrow = datetime.utcnow() + timedelta(days=1)
            cookie["foo"]["expires"] = this_time_tomorrow.strftime(
                "%a, %d %b %Y %H:%M:%S GMT"
            )
            self.send_header("Set-Cookie", cookie["foo"].OutputString())
            self.end_headers()

        def log_message(self, *_: t.Any) -> None:
            pass  # Suppress logging

    with HTTPServer(("localhost", 0), CookieSetter) as server:
        Thread(target=server.serve_forever, daemon=True).start()
        yield server.server_port
        server.shutdown()


@pytest.fixture
def set_cookie(profiles: Path, cookie_server: int) -> t.Iterator[None]:
    """Launch Firefox and visit the cookie-setting server.

    The cookie is set, saved to the DB and the browser closes. Ideally the
    browser should still be running while the cookie tests run, but the
    synchronous playwright API doesn't support that.
    """
    profile_dir = profiles / TEST_PROFILE_DIR
    with sync_playwright() as p, p.firefox.launch_persistent_context(
        user_data_dir=profile_dir
    ) as context:
        context.new_page().goto(
            f"http://localhost:{cookie_server}",
            # Fail quickly because it's localhost. If it's not there in 1s the
            # problem is the server or the test setup, not the network.
            timeout=1000,
        )
    # This `yield` should be indented twice more, inside the launched
    # firefox context manager, but the synchronous playwright API doesn't
    # support it. This means the tests don't test getting cookies while
    # Firefox is running.
    # TODO: Try using the async playwright API instead.
    yield


# _get_profiles_dir_for_os()


@pytest.mark.parametrize(
    "os_name,expected_dir",
    [
        ("linux", "~/.mozilla/firefox"),
        ("macos", "~/Library/Application Support/Firefox/Profiles"),
        ("windows", "~/AppData/Roaming/Mozilla/Firefox/Profiles"),
    ],
)
def test_get_profiles_dir_for_os_valid(
    os_name: str, expected_dir: str
) -> None:
    """Test profile paths for each OS.

    Test only implicit "Firefox" default, since it's the only type we currently
    support.
    """
    profiles_dir = _get_profiles_dir_for_os(os_name, BrowserType.FIREFOX)
    assert profiles_dir == Path(expected_dir).expanduser()


def test_get_profiles_dir_for_os_invalid() -> None:
    """Test invalid OS and browser names."""
    with pytest.raises(ValueError, match="OS must be one of"):
        _get_profiles_dir_for_os("invalid")
    with pytest.raises(
        ValueError, match="'invalid' is not a valid BrowserType"
    ):
        _get_profiles_dir_for_os("linux", BrowserType("invalid"))


# _find_firefox_default_profile()


def test_firefox_get_default_profile_valid(
    profiles_ini_versions: Path,
) -> None:
    """Test discovering the default profile in a valid data dir."""
    profile_dir = profiles_ini_versions / _find_firefox_default_profile(
        profiles_ini_versions
    )
    assert profile_dir.is_dir()
    assert (profile_dir / "cookies.sqlite").is_file()


def test_firefox_get_default_profile_invalid(no_profiles: Path) -> None:
    """Ensure profile discovery in an invalid data dir raises an exception."""
    with pytest.raises(Exception, match="no profiles found"):
        _find_firefox_default_profile(no_profiles)


# _load_firefox_cookie_db()


def test_load_firefox_cookie_db_populated(
    tmp_path: Path, profiles: Path
) -> None:
    """Test loading Firefox cookies DB from a populated profile."""
    db_path = _load_firefox_cookie_db(profiles, tmp_path)
    assert db_path == tmp_path / "cookies.sqlite"
    assert db_path.exists()


@pytest.mark.parametrize("profile_name", [TEST_PROFILE_DIR, None])
def test_load_firefox_cookie_db_unpopulated(
    tmp_path: Path,
    profile_name: t.Optional[str],
    profiles_unpopulated: Path,
) -> None:
    """Test loading Firefox cookies DB from an unpopulated profile."""
    with pytest.raises(FirefoxProfileNotPopulatedError):
        _load_firefox_cookie_db(
            profiles_unpopulated,
            tmp_path,
            profile_name,
        )


def test_load_firefox_cookie_db_copy_error(
    tmp_path: Path, profiles: Path
) -> None:
    """Test loading Firefox cookies DB when copying fails."""
    # deliberately break copy function
    with patch("shutil.copy2"), pytest.raises(
        FileNotFoundError, match="no Firefox cookies DB in temp dir"
    ):
        _load_firefox_cookie_db(
            profiles,
            tmp_path,
            TEST_PROFILE_DIR,
        )


# firefox_cookies()


def test_firefox_cookies(set_cookie: None) -> None:
    """Test getting Firefox cookies after visiting a site with cookies."""
    cookies = t.cast(
        dict, firefox_cookies("http://localhost", TEST_PROFILE_DIR)
    )
    assert len(cookies) > 0
    assert cookies["foo"] == "bar"


def test_warns_for_string_browser(set_cookie: None) -> None:
    """Browser should be passed as `BrowserType` and warns for strings."""
    with pytest.warns(
        DeprecationWarning,
        match=(
            "Please pass `browser` as a `BrowserType` " "instead of `str`."
        ),
    ):
        cookies = t.cast(
            dict,
            firefox_cookies(
                "http://localhost",
                TEST_PROFILE_DIR,
                browser="firefox",  # type: ignore
            ),
        )
    assert len(cookies) > 0
    assert cookies["foo"] == "bar"


def test_firefox_no_cookies(profiles: Path) -> None:
    """Ensure Firefox cookies for an unvisited site are empty."""
    cookies = firefox_cookies("http://example.org", TEST_PROFILE_DIR)
    assert len(cookies) == 0


def test_firefox_cookies_no_scheme() -> None:
    """Ensure Firefox cookies for a URL with no scheme raises an exception."""
    with pytest.raises(
        URLError, match="You must include a scheme with your URL"
    ):
        firefox_cookies("localhost")


def test_firefox_cookies_curl_cookie_file(
    tmp_path: Path, set_cookie: None
) -> None:
    """Test getting Firefox cookies and saving them to a curl cookie file."""
    cookie_file = tmp_path / "cookies.txt"
    firefox_cookies(
        "http://localhost",
        profile_name=TEST_PROFILE_DIR,
        curl_cookie_file=str(cookie_file),
    )
    assert cookie_file.exists()
    assert re.fullmatch(
        (
            r"# Netscape HTTP Cookie File\nlocalhost\tTRUE\t/\tFALSE\t[0-9]+"
            r"\tfoo\tbar\n"
        ),
        cookie_file.read_text(),
    )


@pytest.mark.parametrize("fake_os", ["linux", "darwin", "win32"])
def test_firefox_cookies_os(fake_os: str, profiles: Path) -> None:
    """Ensure the few lines of OS switching code are covered by a test."""
    with patch("sys.platform", fake_os):
        cookies = firefox_cookies("http://example.org", TEST_PROFILE_DIR)
        assert isinstance(cookies, dict)


def test_firefox_cookies_os_invalid(profiles: Path) -> None:
    """Ensure an invalid OS raises an exception."""
    with patch("sys.platform", "invalid"):
        with pytest.raises(OSError):
            firefox_cookies("http://localhost")
