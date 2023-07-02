"""Common code for pycookiecheat."""
from dataclasses import dataclass
from typing import Iterator


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

        See details athttp://www.cookiecentral.com/faq/#3.5
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
