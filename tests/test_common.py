"""Tests for pycookiecheat.common."""

from typing import Iterable

import pytest

from pycookiecheat.common import Cookie, generate_host_keys


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
def test_generate_host_keys(host: str, host_keys: Iterable[str]) -> None:
    """Test `generate_host_keys()` with various example hostnames."""
    assert list(generate_host_keys(host)) == host_keys
