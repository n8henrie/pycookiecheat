import argparse
import json

from .common import BrowserType, write_cookie_file
from .chrome import chrome_cookies
from .firefox import firefox_cookies


def main():
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
    args = parser.parse_args()

    # todo: make this a match statement once MSPV is 3.10

    browser = BrowserType(args.browser)

    if browser == BrowserType.FIREFOX:
        cookie_func = firefox_cookies
    else:
        cookie_func = chrome_cookies

    cookies = cookie_func(
        url=args.url,
        browser=browser,
    )

    if args.output_file:
        write_cookie_file(args.output_file, cookies)
    else:
        print(json.dumps(cookies, indent=4))


if __name__ == "__main__":
    main()
