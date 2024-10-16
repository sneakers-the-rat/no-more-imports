import lazy_import
import collections.abc
import json as jay_son
from typing import List
from collections.abc import Callable
from collections.abc import ChainMap as cm

mod_variable = 10

def imports_are_lazy():
    ast
    typing.List
    re.match('hell ya', 'hell ya')
    # one day you should be able to do this
    # numpy as np

    def a_function(a: typing.Iterable) -> importlib.abc.Finder:
        a = 1

    class AClass():
        zz = 1
        yy = array.array()

        def __init__(self):
            _ = base64.b64decode(f"{binascii.hexlify(b'abc')}")

def regular_names_still_work():
    # assert mod_variable == 10
    x = 20
    # assert x == 20

    def afunc(y, z=1, *args, **kwargs):
        z = 10
        assert z == 10
        assert y == 30

    class AClass():
        z = 1


    afunc(30)

def test_names_are_lazy():
    """
    you can just use the last unique segment
    """
    _ = numpy.random.random(100)
    _ = random

    assert random is numpy.random.random

