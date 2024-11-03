"""Provide a command-line tool for pycookiecheat."""

import argparse
import json
import logging
from importlib.metadata import version

from .common import BrowserType, get_cookies


def _cli() -> None:
    parser = argparse.ArgumentParser(
        prog="pycookiecheat",
        description="Copy cookies from Chrome or Firefox and output as json",
    )
    parser.add_argument("url")
    parser.add_argument(
        "-b", "--browser", type=BrowserType, default=BrowserType.CHROME
    )
    parser.add_argument(
        "-o",
        "--output-file",
        help="Output to this file in netscape cookie file format",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help=(
            "Increase logging verbosity (may repeat), default is "
            "`logging.ERROR`"
        ),
    )
    parser.add_argument(
        "-c",
        "--cookie-file",
        help="Cookie file",
    )
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=version(parser.prog),
    )
    return parser


def main() -> None:
    """Provide a main entrypoint for the command-line tool."""
    parser = _cli()
    args = parser.parse_args()

    logging.basicConfig(level=max(logging.ERROR - 10 * args.verbose, 0))

    # todo: make this a match statement once MSPV is 3.10
    browser = BrowserType(args.browser)

    cookies = get_cookies(
        url=args.url,
        browser=browser,
        curl_cookie_file=args.output_file,
        cookie_file=args.cookie_file,
    )
    if not args.output_file:
        print(json.dumps(cookies, indent=4))


if __name__ == "__main__":
    main()
