"""Tests for pycookiecheat.common."""

import typing as t

import pytest

from pycookiecheat.__main__ import _cli
from pycookiecheat.common import (
    BrowserType,
    Cookie,
    generate_host_keys,
)


@pytest.mark.parametrize(
    "is_secure,is_secure_str",
    [(0, "FALSE"), (1, "TRUE")],
)
def test_cookie_as_cookie_file_line(
    is_secure: int, is_secure_str: str
) -> None:
    """Ensure that `Cookie.as_cookie_file_line()` returns a correct string."""
    cookie = Cookie("foo", "bar", "a.com", "/", 0, is_secure)
    expected = f"a.com\tTRUE\t/\t{is_secure_str}\t0\tfoo\tbar"
    assert cookie.as_cookie_file_line() == expected


@pytest.mark.parametrize(
    "host,host_keys",
    [
        (
            "example.org",
            [
                "example.org",
                ".example.org",
            ],
        ),
        (
            "foo.bar.example.org",
            [
                "example.org",
                ".example.org",
                "bar.example.org",
                ".bar.example.org",
                "foo.bar.example.org",
                ".foo.bar.example.org",
            ],
        ),
        ("localhost", ["localhost"]),
    ],
)
def test_generate_host_keys(host: str, host_keys: t.Iterable[str]) -> None:
    """Test `generate_host_keys()` with various example hostnames."""
    assert list(generate_host_keys(host)) == host_keys


def test_cli() -> None:
    """Test the cli.
    When cli tests fail, it probably means that examples in the readme need to
    be updated, and likely a "leftmost non-zero version number" bump to reflect
    an API change.
    """
    args = _cli().parse_args(["https://n8henrie.com"])
    assert args.url == "https://n8henrie.com"
    assert args.browser == BrowserType.CHROME

    args = _cli().parse_args(["github.com", "-vv"])
    assert args.verbose == 2

    args = _cli().parse_args(["n8henrie.com", "--browser", "firefox"])
    assert args.browser == BrowserType.FIREFOX
