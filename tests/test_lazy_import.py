import lazy_import
from typing import List
import collections.abc
from collections.abc import Callable
from collections.abc import ChainMap as cm

mod_variable = 10

def test_imports_are_lazy():
    re.match('hell ya', 'hell ya')
    typing.List

def test_regular_names_still_work():
    assert mod_variable == 10
    x = 20
    assert x == 20

    def afunc(y):
        z = 10
        assert z == 10
        assert y == 30

    afunc(30)

def test_names_are_lazy():
    """
    you can just use the last unique segment
    """
    _ = numpy.random.random(100)
    _ = random

    assert random is numpy.random.random

