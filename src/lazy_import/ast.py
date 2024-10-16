import ast
from collections import ChainMap
from dataclasses import dataclass, field
from pathlib import Path

@dataclass
class Name:

    module: str
    name: str | None = None
    aliases: set = field(default_factory=set)

    def __contains__(self, item: str):
        return item in self.aliases or (
            item == self.module
            if self.name is None else
            item == self.name
        )

    @classmethod
    def from_ast_name(cls, name: ast.Name) -> 'Name':
        return cls.from_str(name.id)

    @classmethod
    def from_str(cls, name: str) -> 'Name':
        if len(name_parts := name.rsplit(".")) > 1:
            return Name(module=name_parts[0], name=name_parts[1])
        else:
            return Name(module=name)

@dataclass
class NameCollection:

    names: list[Name] = field(default_factory=set)

    def add(self, new_name: ast.Name):
        for name in self.names:
            if new_name.id in name:
                name.aliases.add(new_name.id)
                return
        self.names.append(Name.from_ast_name(new_name))

class NameVisitor(ast.NodeVisitor):
    """
    Extract names to import and assign from an importless python module
    """

    def __init__(self):
        self.real_names = ChainMap()
        self.fake_names = NameCollection()

    def pop_ctx(self):
        self.real_names = self.real_names.parents

    def push_ctx(self):
        self.real_names = self.real_names.new_child()

    def visit_Import(self, node: ast.Import | ast.ImportFrom) -> None:
        """Add to names"""
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            self.real_names[name] = node

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Add to names"""
        self.visit_Import(node)


    def visit_Name(self, node: ast.Name):
        """Either add to real names or fake names depending on ctx"""
        if node.ctx == ast.Store():
            self.real_names[node.id] = node
        elif node.ctx == ast.Load() and node.id not in self.real_names:
            self.fake_names.add(node)
        elif node.ctx == ast.Del() and node.id in self.real_names:
            del self.real_names[node.id]
        else:  # pragma: no cover
            if node.ctx not in (ast.Del(), ast.Store(), ast.Load()):
                raise ValueError('How did this happen!? wrong node ctx type?')

    def visit_Attribute(self, node: ast.Attribute):
        attr_name = flatten_attribute(node)
        if node.ctx == ast.Load():
            if attr_name not in self.real_names:
                self.fake_names.add(Name.from_str(attr_name))
        elif node.ctx == ast.Store():
            self.real_names[attr_name] = node
        elif node.ctx == ast.Del() and attr_name in self.real_names:
            del self.real_names[attr_name]
        else:  # pragma: no cover
            if node.ctx not in (ast.Del(), ast.Store(), ast.Load()):
                raise ValueError('How did this happen!? wrong node ctx type?')

    def visit_FunctionDef(self, node):
        """push context"""

        self.push_ctx()
        args = node.args
        for arg in args.args:
            self.real_names[arg.arg] = arg
        if args.vararg:
            self.real_names[args.vararg.arg] = args.vararg
        if args.kwarg:
            self.real_names[args.kwarg.arg] = args.kwarg

    def visit_AsyncFunctionDef(self, node):
        """push context"""
        self.push_ctx()

    def visit_ClassDef(self, node):
        """push context"""
        self.push_ctx()

    def visit_Return(self, node):
        """pop context"""
        self.pop_ctx()


def flatten_attribute(attr: ast.Attribute) -> str:
    if isinstance(attr.value, ast.Attribute):
        return '.'.join([flatten_attribute(attr.value), attr.attr])
    elif isinstance(attr.value, ast.Name):
        return '.'.join([attr.value.id, attr.attr])
