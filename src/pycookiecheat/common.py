"""Common code for pycookiecheat."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum, unique
from pathlib import Path
from typing import Iterator
from warnings import warn

logger = logging.getLogger(__name__)


@dataclass
class Cookie:
    """Internal helper class used to represent a cookie only during processing.

    Cookies returned to the user from the public API are dicts, not instances
    of this class.
    """

    name: str
    value: str
    host_key: str
    path: str
    expires_utc: int
    is_secure: int

    def as_cookie_file_line(self) -> str:
        """Return a string for a Netscape-style cookie file usable by curl.

        See details at http://www.cookiecentral.com/faq/#3.5
        """
        return "\t".join(
            [
                self.host_key,
                "TRUE",
                self.path,
                "TRUE" if self.is_secure else "FALSE",
                str(self.expires_utc),
                self.name,
                self.value,
            ]
        )


def generate_host_keys(hostname: str) -> Iterator[str]:
    """Yield keys for `hostname`, from least to most specific.

    Given a hostname like foo.example.com, this yields the key sequence:

    example.com
    .example.com
    foo.example.com
    .foo.example.com

    Treat "localhost" explicitly by returning only itself.
    """
    if hostname == "localhost":
        yield hostname
        return

    labels = hostname.split(".")
    for i in range(2, len(labels) + 1):
        domain = ".".join(labels[-i:])
        yield domain
        yield "." + domain


def deprecation_warning(msg: str) -> None:
    """Raise a deprecation warning with the provided message.

    `stacklevel=3` tries to show the appropriate calling code to the user.
    """
    warn(msg, DeprecationWarning, stacklevel=3)


@unique
class BrowserType(str, Enum):
    """Provide discrete values for recognized browsers.

    This utility class helps ensure that the requested browser is specified
    precisely or fails early by matching against user input; internally this
    enum should be preferred as compared to passing strings.

    >>> "chrome" is BrowserType.CHROME
    True

    TODO: consider using `enum.StrEnum` once pycookiecheat depends on python >=
    3.11
    """

    BRAVE = "brave"
    CHROME = "chrome"
    CHROMIUM = "chromium"
    FIREFOX = "firefox"
    SLACK = "slack"

    # https://mypy.readthedocs.io/en/stable/common_issues.html#incompatible-overrides
    @classmethod
    def _missing_(cls, value: str) -> BrowserType:  # type: ignore[override]
        """Provide case-insensitive matching for input values.

        >>> BrowserType("chrome")
        <BrowserType.CHROME: 'chrome'>
        >>> BrowserType("FiReFoX")
        <BrowserType.FIREFOX: 'firefox'>
        >>> BrowserType("edge")
        Traceback (most recent call last):
        ValueError: 'edge' is not a valid BrowserType
        """
        folded = value.casefold()
        for member in cls:
            if member.value == folded:
                return member
        raise ValueError(f"{value!r} is not a valid {cls.__qualname__}")


def write_cookie_file(path: Path | str, cookies: list[Cookie]) -> None:
    """Write cookies to a file in Netscape Cookie File format."""
    path = Path(path)
    # Some programs won't recognize this as a valid cookie file without the
    # header
    output = (
        "\n".join(
            ["# Netscape HTTP Cookie File"]
            + [c.as_cookie_file_line() for c in cookies]
        )
        + "\n"
    )
    path.write_text(output)
