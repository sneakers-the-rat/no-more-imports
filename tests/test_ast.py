import ast

from no_more_imports.ast import Name, NameCollection, NameVisitor

from .conftest import DATA_DIR


def test_find_fake_names():
    expected = NameCollection(
        names=[
            Name(module="ast", name=None, aliases=set()),
            Name(module="typing", name="List", aliases=set()),
            Name(module="re", name="match", aliases={"match"}),
            Name(module="importlib.abc", name="Finder", aliases=set()),
            Name(module="os.path", name="basename", aliases=set()),
            Name(module="pathlib", name="Path", aliases=set()),
            Name(module="array", name="array", aliases=set()),
            Name(module="base64", name="b64decode", aliases=set()),
            Name(module="binascii", name="hexlify", aliases=set()),
            Name(module="random", name="randint", aliases={"randint"}),
        ]
    )

    with open(DATA_DIR / "input_file.py", "r") as sfile:
        source_code = sfile.read()

    node = ast.parse(source_code)
    visitor = NameVisitor()
    visitor.visit(node)
    assert visitor.fake_names == expected
