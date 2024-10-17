import no_more_imports


mod_variable = 10


def test_imports_are_lazy():
    re.match("hell ya", "hell ya")
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
    _ = random.randint(1, 10)
    _ = randint(1, 10)

    assert randint is random.randint


def test_even_installs_are_lazy():
    """
    whatever, if we don't even have the package we'll try to get it
    """
    res = subprocess.run(['python', '-m', 'pip', 'uninstall', 'numpy', '-y'])
    assert res.returncode == 0

    data = numpy.zeros((2,2))
    assert numpy.array_equal(data, numpy.zeros((2,2)))
