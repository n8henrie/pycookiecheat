"""__init__.py :: Exposes chrome_cookies function."""

from pycookiecheat.chrome import chrome_cookies
from pycookiecheat.common import BrowserType
from pycookiecheat.firefox import firefox_cookies

__author__ = "Nathan Henrie"
__email__ = "nate@n8henrie.com"
__version__ = "v0.7.0"

__all__ = [
    "BrowserType",
    "chrome_cookies",
    "firefox_cookies",
]
