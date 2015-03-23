# -*- coding: utf-8 -*-

"""
test_pycookiecheat
----------------------------------

Tests for `pycookiecheat` module.
"""

from pycookiecheat import chrome_cookies
from uuid import uuid4
import pytest
import os


def test_raises_on_empty():
    with pytest.raises(TypeError):
        broken = chrome_cookies()


def test_no_cookies():
    if os.getenv('TRAVIS', False) == 'true':
        never_been_here = 'http://{}.com'.format(uuid4())
        empty_dict = chrome_cookies(never_been_here)
        assert empty_dict == dict()
    else:
        assert True


def test_n8henrie_com():
    """Tests a wordpress cookie that I think should be set. NB: Will fail
    unless you've visited my site in Chrome."""
    if os.getenv('TRAVIS', False) == 'true':
        cookies = chrome_cookies('http://n8henrie.com')
        assert cookies['wordpress_test_cookie'] == 'WP+Cookie+check'
    else:
        assert True
