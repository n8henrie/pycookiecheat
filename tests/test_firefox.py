from collections.abc import Iterator
from pathlib import Path
from datetime import datetime
from datetime import timedelta
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler
from http.server import HTTPServer
import random
import string
import tempfile
from threading import Thread
from unittest.mock import patch

from playwright.sync_api import sync_playwright
import pytest

from pycookiecheat import firefox_cookies
import pycookiecheat.firefox


### _get_profiles_dir_for_os()


@pytest.mark.parametrize(
    "os_name,expected_dir",
    [
        ("linux", "~/.mozilla/firefox"),
        ("osx", "~/Library/Application Support/Firefox/Profiles"),
        ("windows", "~/AppData/Roaming/Mozilla/Firefox/Profiles"),
    ],
)
def test_get_profiles_dir_for_os_valid(os_name, expected_dir):
    # Test only implicit "Firefox" default, since it's the only type we
    # currently support
    profiles_dir = pycookiecheat.firefox._get_profiles_dir_for_os(
        os_name, "Firefox"
    )
    assert profiles_dir == Path(expected_dir).expanduser()


def test_get_profiles_dir_for_os_invalid():
    with pytest.raises(ValueError, match="OS must be one of"):
        pycookiecheat.firefox._get_profiles_dir_for_os(
            "invalid"  # type: ignore
        )
    with pytest.raises(ValueError, match="Browser must be one of"):
        pycookiecheat.firefox._get_profiles_dir_for_os("linux", "invalid")


### _find_firefox_default_profile()


PROFILES_INI_VERSION1 = """[General]
StartWithLastProfile=1

[Profile0]
Name=fake-profile
IsRelative=1
Path={profile_name}
Default=1

[Profile1]
Name=fake-profile2
IsRelative=1
Path=abcdef01.fake-profile2
"""

PROFILES_INI_VERSION2 = """[Install8149948BEF895A0D]
Default={profile_name}
Locked=1

[General]
StartWithLastProfile=1
Version=2

[Profile0]
Name=fake-profile
IsRelative=1
Path={profile_name}
Default=1
"""

PROFILES_INI_EMPTY = """[General]
StartWithLastProfile=1
Version=2
"""


def _make_fake_firefox_profiles_dir(request: pytest.FixtureRequest):
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        tmp_path.mkdir(exist_ok=True)
        profile_prefix = "".join(
            random.choices(string.ascii_lowercase + string.digits, k=8)
        )
        profile_name = profile_prefix + ".fake-profile"
        profile_dir = tmp_path / profile_name
        profile_dir.mkdir()
        (tmp_path / "profiles.ini").write_text(
            request.param.format(profile_name=profile_name)
        )
        # Start firefox once with fake profile path to populate it
        with sync_playwright() as p:
            context = p.firefox.launch_persistent_context(
                user_data_dir=str(profile_dir),
                headless=True,
            )
            context.close()
        yield tmp_path


@pytest.fixture(
    scope="module", params=[PROFILES_INI_VERSION1, PROFILES_INI_VERSION2]
)
def firefox_profiles_dir(request: pytest.FixtureRequest):
    yield from _make_fake_firefox_profiles_dir(request)


@pytest.fixture(scope="module", params=[PROFILES_INI_EMPTY])
def firefox_profiles_dir_no_profiles(request: pytest.FixtureRequest):
    yield from _make_fake_firefox_profiles_dir(request)


def test_firefox_get_default_profile_valid(firefox_profiles_dir):
    """Test getting the default profile."""
    profile_dir = (
        firefox_profiles_dir
        / pycookiecheat.firefox._find_firefox_default_profile(
            firefox_profiles_dir
        )
    )
    assert profile_dir.is_dir()
    assert (profile_dir / "cookies.sqlite").is_file()


def test_firefox_get_default_profile_invalid(firefox_profiles_dir_no_profiles):
    """Test getting the profiles when there are no profiles."""
    with pytest.raises(Exception, match="no profiles found"):
        pycookiecheat.firefox._find_firefox_default_profile(
            firefox_profiles_dir_no_profiles
        )


### firefox_cookies()


@pytest.fixture(scope="module")
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

    with HTTPServer(("localhost", 0), CookieSetter) as server:
        Thread(target=server.serve_forever, daemon=True).start()
        yield server.server_port


@pytest.fixture(scope="module")
def cookie_site_visited(
    firefox_profiles_dir: Path, cookie_server: int
) -> Iterator[Path]:
    with patch(
        "pycookiecheat.firefox._get_profiles_dir_for_os",
        autospec=True,
        return_value=firefox_profiles_dir,
    ):
        profile_dir = next(firefox_profiles_dir.glob("*.fake-profile"))
        with sync_playwright() as p:
            with p.firefox.launch_persistent_context(
                user_data_dir=profile_dir
            ) as context:
                context.new_page().goto(
                    f"http://localhost:{cookie_server}",
                    # Smaller 100ms timeout since the server is on localhost.
                    # If it's not there in 100ms the problem is the server or
                    # the test setup, not the network. -> Fail quickly.
                    timeout=100,
                )
        # This `yield` should be indented twice more, inside the launched
        # firefox context manager, but the synchronous playwright API doesn't
        # support it. This means the tests don't test getting cookies while
        # Firefox is running.
        # TODO: Try using the async playwright API instead.
        yield firefox_profiles_dir


def test_firefox_cookies(cookie_site_visited):
    profile = next(
        filter(
            lambda l: "fake-profile" in l.name,
            cookie_site_visited.iterdir(),
        )
    )
    cookies = firefox_cookies("http://localhost", profile_name=profile.name)
    assert len(cookies) > 0
    assert cookies["foo"] == "bar"
