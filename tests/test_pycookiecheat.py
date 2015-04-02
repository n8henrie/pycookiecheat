"""test_pycookiecheat.py
Tests for `pycookiecheat` module.
"""

from pycookiecheat import chrome_cookies
from uuid import uuid4
import pytest
import os
import os.path
import sys
import shutil


@pytest.fixture(scope='module')
def travis_setup():
    if (os.getenv('TRAVIS', False) == 'true') and (sys.platform == 'linux'):
        cookies_dest = os.path.expanduser('~/.config/chromium/Default')
        curdir = os.path.dirname(os.path.abspath(__file__))
        cookies_path = os.path.join(curdir, 'Cookies')

        os.mkdirs(cookies_dest)
        shutil.copy(cookies_path, cookies_dest)


def test_raises_on_empty():
    with pytest.raises(TypeError):
        broken = chrome_cookies()
        return broken


def test_no_cookies(travis_setup):
    never_been_here = 'http://{}.com'.format(uuid4())
    empty_dict = chrome_cookies(never_been_here)
    assert empty_dict == dict()


def test_fake_cookie(travis_setup):
    """Tests a fake cookie from the website below. For this to pass, you'll
    have to visit the url and put in "TestCookie" and "Just_a_test!" to set
    a temporary cookie with the appropriate values."""
    cookies = chrome_cookies('http://www.html-kit.com/tools/cookietester')
    assert cookies['TestCookie'] == 'Just_a_test!'
