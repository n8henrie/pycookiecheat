from collections.abc import Iterator
from collections.abc import Mapping
from dataclasses import dataclass


@dataclass
class Cookie:
    key: str
    value: str
    host: str
    path: str
    expiry: int
    is_secure: bool

    @classmethod
    def from_firefox(cls, row: Mapping) -> "Cookie":
        return cls(
            key=row["name"],
            value=row["value"],
            host=row["host"],
            path=row["path"],
            expiry=row["expiry"],
            is_secure=bool(int(row["isSecure"])),
        )

    @classmethod
    def from_chrome(
        cls,
        key: str,
        value: str,
        host: str,
        path: str,
        expiry: int,
        is_secure: bool,
    ) -> "Cookie":
        return cls(key, value, host, path, expiry, is_secure)

    def as_cookie_file_line(self) -> str:
        # http://www.cookiecentral.com/faq/#3.5
        return "\t".join(
            [
                self.host,
                "TRUE",
                self.path,
                "TRUE" if self.is_secure else "FALSE",
                str(self.expiry),
                self.key,
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
