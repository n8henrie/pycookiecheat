"""test_pycookiecheat.py
Tests for pycookiecheat module.
"""

from pycookiecheat import chrome_cookies
from uuid import uuid4
import pytest
import os
import os.path
import sys
import shutil


@pytest.fixture(scope='module')
def travis_setup(request):
    """Sets up chromium's cookies file and directory if it seems to be running
    on travis-ci. Appropriately doesn't load teardown() this dir already
    exists, preventing it from getting to the teardown function which would
    otherwise risk deleting someone's ~/.config/chromium directory (if they had
    the TRAVIS=true environment set for some reason)."""

    def teardown():
        os.remove(cookies_dest)
        try:
            os.removedirs(cookies_dest_dir)
        except OSError:
            # Directory wasn't empty, expected at '~'
            pass

    # Where the cookies file should be
    cookies_dest_dir = os.path.expanduser('~/.config/chromium/Default')
    cookies_dest = os.path.join(cookies_dest_dir, 'Cookies')

    # Where the test cookies file is
    cookies_dir = os.path.dirname(os.path.abspath(__file__))
    cookies_path = os.path.join(cookies_dir, 'Cookies')

    if all([os.getenv('TRAVIS') == 'true',
           sys.platform.startswith('linux'),
           not os.path.isfile(cookies_dest)]):

        os.makedirs(cookies_dest_dir)
        shutil.copy(cookies_path, cookies_dest_dir)

        # Only teardown if running on travis
        request.addfinalizer(teardown)
        return
    # Not running on travis, just return since nothing should have been made.
    return


def test_raises_on_empty():
    with pytest.raises(TypeError):
        broken = chrome_cookies()
        return broken


def test_no_cookies(travis_setup):
    never_been_here = 'http://{0}.com'.format(uuid4())
    empty_dict = chrome_cookies(never_been_here)
    assert empty_dict == dict()


def test_fake_cookie(travis_setup):
    """Tests a fake cookie from the website below. For this to pass, you'll
    have to visit the url and put in "TestCookie" and "Just_a_test!" to set
    a temporary cookie with the appropriate values."""
    cookies = chrome_cookies('http://www.html-kit.com/tools/cookietester')
    assert cookies['TestCookie'] == 'Just_a_test!'
