import no_more_imports
import collections.abc
import json as jay_son
from typing import List
from collections.abc import Callable
from collections import ChainMap as cm

mod_variable = 10

my_list = [1, 2, 3]
my_dict = {"a": 1, "b": 2}
list_comprehension = [item for item in my_list]
dict_comprehension = {key: val for key, val in my_dict.items()}

for item in my_list:
    zzz = 1


def imports_are_lazy():
    ast
    typing.List
    re.match("hell ya", "hell ya")
    match("hell ya again", "hell ya again")
    # one day you should be able to do this
    # numpy as np

    def a_function(a: typing.Iterable) -> importlib.abc.Finder:
        a = 1

    def another_function(a: "pathlib.Path") -> "os.path.basename":
        pass

    class AClass:
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

    class AClass:
        z = 1

    afunc(30)


def test_names_are_lazy():
    """
    you can just use the last unique segment
    """
    _ = random.randint(1, 10)
    _ = randint(1, 10)

    a = numpy.random.default_rng()
    ints = a.integers((1,2))

    assert randint is random.randint


