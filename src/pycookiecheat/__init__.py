"""__init__.py :: Exposes chrome_cookies function."""

from pycookiecheat.pycookiecheat import chrome_cookies
from pycookiecheat.firefox import firefox_cookies

__author__ = "Nathan Henrie"
__email__ = "nate@n8henrie.com"
__version__ = "v0.5.0"

__all__ = [
    "chrome_cookies",
    "firefox_cookies",
]
