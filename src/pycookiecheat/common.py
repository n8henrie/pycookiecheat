from collections.abc import Iterator


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
