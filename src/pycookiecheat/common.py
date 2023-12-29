"""Common code for pycookiecheat."""
from dataclasses import dataclass
from enum import auto, Enum
from typing import Iterator
from warnings import warn


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


def _deprecation_warning(msg: str):
    warn(msg, DeprecationWarning, stacklevel=3)


class BrowserType(str, Enum):
    """Provide discrete values for recognized browsers.

    This utility class helps ensure that the requested browser is specified
    precisely or fails early by matching against user input; internally this
    enum should be preferred as compared to passing strings.

    >>> "chrome" == BrowserType.CHROME
    True

    TODO: consider using `enum.StrEnum` once pycookiecheat depends on python >=
    3.11
    """

    BRAVE = "brave"
    CHROME = "chrome"
    CHROMIUM = "chromium"
    FIREFOX = "firefox"
    SLACK = "slack"

    @classmethod
    def _missing_(cls, value: str):
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
        raise ValueError("%r is not a valid %s" % (value, cls.__qualname__))
