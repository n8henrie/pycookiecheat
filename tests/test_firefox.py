from datetime import datetime
from datetime import timedelta
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler
from http.server import HTTPServer
from pathlib import Path
import re
from textwrap import dedent
from threading import Thread
from typing import Iterator
from typing import Optional
from unittest.mock import patch
from urllib.error import URLError

from playwright.sync_api import sync_playwright
import pytest
from pytest import FixtureRequest
from pytest import TempPathFactory

from pycookiecheat.firefox import _find_firefox_default_profile
from pycookiecheat.firefox import _get_profiles_dir_for_os
from pycookiecheat.firefox import _load_firefox_cookie_db
from pycookiecheat.firefox import firefox_cookies
from pycookiecheat.firefox import FirefoxProfileNotPopulatedError


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
) -> Iterator[Path]:
    """
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
def profiles(tmp_path_factory: TempPathFactory) -> Iterator[Path]:
    """Create a populated Firefox data dir with a profile & cookie DB"""
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
) -> Iterator[Path]:
    """
    Create a populated Firefox data dir using varius `profiles.ini` file format
    versions and contents.
    """
    yield from _make_test_profiles(tmp_path_factory.mktemp("_"), request.param)


@pytest.fixture(scope="module")
def no_profiles(tmp_path_factory: TempPathFactory) -> Iterator[Path]:
    """Create a Firefox data dir with a `profiles.ini` but no profiles."""
    yield from _make_test_profiles(
        tmp_path_factory.mktemp("_"), PROFILES_INI_EMPTY
    )


# TODO: Making this fixture module-scoped breaks the tests using the `profiles`
#       fixture. Find out why.
@pytest.fixture
def profiles_unpopulated(tmp_path: Path) -> Iterator[Path]:
    """
    Create a Firefox data dir with a valid `profiles.ini` file, but an
    unpopulated (i.e. never-used) profile dir.
    """
    yield from _make_test_profiles(
        tmp_path, PROFILES_INI_VERSION2, populate=False
    )


@pytest.fixture(scope="session")
def cookie_server() -> Iterator[int]:
    """
    Start an `HTTPServer` on localhost which replies to GET requests by
    setting a cookie. Used as fixture for testing cookie retrieval.

    Returns:
        The port of the server on localhost.
    """

    class CookieSetter(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            cookie = SimpleCookie()
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

        def log_message(self, *_):
            pass  # Suppress logging

    with HTTPServer(("localhost", 0), CookieSetter) as server:
        Thread(target=server.serve_forever, daemon=True).start()
        yield server.server_port
        server.shutdown()


@pytest.fixture
def set_cookie(profiles: Path, cookie_server: int) -> Iterator[None]:
    """
    Launch Firefox and visit the cookie-setting server. The cookie is set,
    saved to the DB and the browser closes. Ideally the browser should still
    be running while the cookie tests run, but the synchronous playwright API
    doesn't support that.
    """
    profile_dir = profiles / TEST_PROFILE_DIR
    with sync_playwright() as p, p.firefox.launch_persistent_context(
        user_data_dir=profile_dir
    ) as context:
        context.new_page().goto(
            f"http://localhost:{cookie_server}",
            # Fail quickly because it's localhost. If it's not there in 100ms
            # the problem is the server or the test setup, not the network.
            timeout=100,
        )
    # This `yield` should be indented twice more, inside the launched
    # firefox context manager, but the synchronous playwright API doesn't
    # support it. This means the tests don't test getting cookies while
    # Firefox is running.
    # TODO: Try using the async playwright API instead.
    yield


### _get_profiles_dir_for_os()


@pytest.mark.parametrize(
    "os_name,expected_dir",
    [
        ("linux", "~/.mozilla/firefox"),
        ("osx", "~/Library/Application Support/Firefox/Profiles"),
        ("windows", "~/AppData/Roaming/Mozilla/Firefox/Profiles"),
    ],
)
def test_get_profiles_dir_for_os_valid(os_name: str, expected_dir: str):
    # Test only implicit "Firefox" default, since it's the only type we
    # currently support
    profiles_dir = _get_profiles_dir_for_os(os_name, "Firefox")
    assert profiles_dir == Path(expected_dir).expanduser()


def test_get_profiles_dir_for_os_invalid():
    with pytest.raises(ValueError, match="OS must be one of"):
        _get_profiles_dir_for_os("invalid")
    with pytest.raises(ValueError, match="Browser must be one of"):
        _get_profiles_dir_for_os("linux", "invalid")


### _find_firefox_default_profile()


def test_firefox_get_default_profile_valid(profiles_ini_versions: Path):
    profile_dir = profiles_ini_versions / _find_firefox_default_profile(
        profiles_ini_versions
    )
    assert profile_dir.is_dir()
    assert (profile_dir / "cookies.sqlite").is_file()


def test_firefox_get_default_profile_invalid(no_profiles: Path):
    with pytest.raises(Exception, match="no profiles found"):
        _find_firefox_default_profile(no_profiles)


### _load_firefox_cookie_db()


def test_load_firefox_cookie_db_populated(tmp_path: Path, profiles: Path):
    db_path = _load_firefox_cookie_db(profiles, tmp_path)
    assert db_path == tmp_path / "cookies.sqlite"
    assert db_path.exists()


@pytest.mark.parametrize("profile_name", [TEST_PROFILE_DIR, None])
def test_load_firefox_cookie_db_unpopulated(
    tmp_path: Path,
    profile_name: Optional[str],
    profiles_unpopulated: Path,
):
    with pytest.raises(FirefoxProfileNotPopulatedError):
        _load_firefox_cookie_db(
            profiles_unpopulated,
            tmp_path,
            profile_name,
        )


def test_load_firefox_cookie_db_copy_error(tmp_path: Path, profiles: Path):
    # deliberately break copying
    with patch("shutil.copy2"), pytest.raises(
        FileNotFoundError, match="no Firefox cookies DB in temp dir"
    ):
        _load_firefox_cookie_db(
            profiles,
            tmp_path,
            TEST_PROFILE_DIR,
        )


### firefox_cookies()


def test_firefox_cookies(set_cookie: None):
    cookies = firefox_cookies("http://localhost", TEST_PROFILE_DIR)
    assert len(cookies) > 0
    assert cookies["foo"] == "bar"


def test_firefox_no_cookies(profiles: Path):
    cookies = firefox_cookies("http://example.org", TEST_PROFILE_DIR)
    assert len(cookies) == 0


def test_firefox_cookies_no_scheme():
    with pytest.raises(
        URLError, match="You must include a scheme with your URL"
    ):
        firefox_cookies("localhost")


def test_firefox_cookies_curl_cookie_file(tmp_path: Path, set_cookie: None):
    cookie_file = tmp_path / "cookies.txt"
    firefox_cookies(
        "http://localhost",
        profile_name=TEST_PROFILE_DIR,
        curl_cookie_file=str(cookie_file),
    )
    assert cookie_file.exists()
    assert re.fullmatch(
        r"localhost\tTRUE\t/\tFALSE\t[0-9]+\tfoo\tbar\n",
        cookie_file.read_text(),
    )


@pytest.mark.parametrize("fake_os", ["linux", "darwin", "win32"])
def test_firefox_cookies_os(fake_os, profiles: Path):
    with patch("sys.platform", fake_os):
        cookies = firefox_cookies("http://example.org", TEST_PROFILE_DIR)
        assert isinstance(cookies, dict)


def test_firefox_cookies_os_invalid(profiles: Path):
    with patch("sys.platform", "invalid"):
        with pytest.raises(OSError):
            firefox_cookies("http://localhost")
