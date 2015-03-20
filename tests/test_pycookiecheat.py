# -*- coding: utf-8 -*-

"""
test_pycookiecheat
----------------------------------

Tests for `pycookiecheat` module.
"""

from pycookiecheat import chrome_cookies
from uuid import uuid4
import pytest

def test_raises_on_empty():
    with pytest.raises(TypeError):
        broken = chrome_cookies()

def test_no_cookies():
    never_been_here = 'http://{}.com'.format(uuid4())
    empty_dict = chrome_cookies(never_been_here)
    assert empty_dict == dict()

def test_n8henrie_com():
    """Tests a wordpress cookie that I think should be set. NB: Will fail unless you've visited my site in Chrome."""
    cookies = chrome_cookies('http://n8henrie.com')
    assert cookies['wordpress_test_cookie'] == 'WP+Cookie+check'
