"""Provide a command-line tool for pycookiecheat."""

import argparse
import json
import logging

from .chrome import chrome_cookies
from .common import BrowserType
from .firefox import firefox_cookies


def main() -> None:
    """Provide a main entrypoint for the command-line tool."""
    parser = argparse.ArgumentParser(
        prog="pycookiecheat",
        description="Copy cookies from Chrome or Firefox and output as json",
    )
    parser.add_argument(
        "-u", "--url", required=True, help="requires scheme (e.g. `https://`)"
    )
    parser.add_argument("-b", "--browser", default="Chrome")
    parser.add_argument(
        "-o",
        "--output-file",
        help="Output to this file in netscape cookie file format",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="count",
        default=0,
        help=(
            "Increase logging verbosity (may repeat), default is "
            "`logging.ERROR`"
        ),
    )
    args = parser.parse_args()

    logging.basicConfig(level=max(logging.ERROR - 10 * args.verbose, 0))

    # todo: make this a match statement once MSPV is 3.10
    browser = BrowserType(args.browser)

    # Use separate function calls to make it easier to add other command line
    # line flags in the future
    if browser == BrowserType.FIREFOX:
        cookies = firefox_cookies(
            url=args.url,
            browser=browser,
            curl_cookie_file=args.output_file,
        )
    else:
        cookies = chrome_cookies(
            url=args.url,
            browser=browser,
            curl_cookie_file=args.output_file,
        )

    if not args.output_file:
        print(json.dumps(cookies, indent=4))


if __name__ == "__main__":
    main()
