import ast
from collections import ChainMap
from collections.abc import Container
from dataclasses import dataclass, field
from typing import Iterator, Literal, overload


@dataclass(eq=True)
class Name:

    module: str
    name: str | None = None
    aliases: set[str] = field(default_factory=set)

    def __contains__(self, item: str):
        return item in self.aliases or (
            item == self.module if self.name is None else item in (self.name, self.id)
        )

    @property
    def id(self) -> str:
        if self.name is None:
            return self.module
        else:
            return ".".join([self.module, self.name])

    @property
    def parts(self) -> list[str]:
        """
        All the subparts of the fully qualified name

        Eg if we were `module.submodule.subsubmodule.A`

        this would be
        - `module`
        - `module.submodule`
        - `module.submodule.submodule`
        - `module.submodule.subsubmodule.A`

        """
        subparts = self.module.split(".")
        if self.name:
            subparts.append(self.name)
        return [".".join(subparts[: i + 1]) for i in range(len(subparts))]

    def in_dict(self, other: Container):
        return any(part in other for part in self.parts)

    @classmethod
    def from_ast_name(cls, name: ast.Name) -> "Name":
        return cls.from_str(name.id)

    @classmethod
    def from_str(cls, name: str) -> "Name":
        if len(name_parts := name.rsplit(".", maxsplit=1)) > 1:
            return Name(module=name_parts[0], name=name_parts[1])
        else:
            return Name(module=name)


@dataclass(eq=True)
class NameCollection:

    names: list[Name] = field(default_factory=list)

    def add(self, new_name: ast.Name | Name):
        if isinstance(new_name, ast.Name):
            new_name = Name.from_ast_name(new_name)

        for name in self.names:

            if new_name.module == name.name and not new_name.name:
                # Make an alias if we have something that exists for this already
                name.aliases.add(new_name.module)
                return
            elif new_name.module == name.module:
                # Otherwise we have something that we're going to import already and skip
                return

        self.names.append(new_name)

    def __iter__(self) -> Iterator[Name]:
        yield from self.names


class NameVisitor(ast.NodeVisitor):
    """
    Extract names to import and assign from an importless python module
    """

    def __init__(self):
        self.real_names = ChainMap({"self": None}, globals()["__builtins__"])
        self.fake_names = NameCollection()

    def pop_ctx(self):
        self.real_names = self.real_names.parents
        self.filter_fake_names()

    def push_ctx(self):
        self.real_names = self.real_names.new_child()

    def visit_Import(self, node: ast.Import | ast.ImportFrom) -> None:
        """Add to names"""
        # print(ast.dump(node))
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            self.real_names[name] = node

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Add to names"""
        return self.visit_Import(node)

    def visit_Name(self, node: ast.Name):
        """Either add to real names or fake names depending on ctx"""
        # print(ast.dump(node))
        if isinstance(node.ctx, ast.Store):
            self.real_names[node.id] = node
        elif isinstance(node.ctx, ast.Load):
            name = Name.from_ast_name(node)
            if not name.in_dict(self.real_names):
                self.fake_names.add(name)
        elif isinstance(node.ctx, ast.Del) and node.id in self.real_names:
            del self.real_names[node.id]
        else:  # pragma: no cover
            if type(node.ctx) not in (ast.Del, ast.Store, ast.Load):
                raise ValueError(f"How did this happen!? wrong node ctx type? {node.ctx}")

    def visit_Attribute(self, node: ast.Attribute):
        # print(ast.dump(node))
        attr_name = flatten_attribute(node)
        if attr_name is None:
            return

        if isinstance(node.ctx, ast.Load):
            name = Name.from_str(attr_name)
            if not name.in_dict(self.real_names):
                self.fake_names.add(name)
        elif isinstance(node.ctx, ast.Store):
            self.real_names[attr_name] = node
        elif isinstance(node.ctx, ast.Del) and attr_name in self.real_names:
            del self.real_names[attr_name]
        else:  # pragma: no cover
            if type(node.ctx) not in (ast.Del, ast.Store, ast.Load):
                raise ValueError(f"How did this happen!? wrong node ctx type? {node.ctx}")

    def visit_FunctionDef(self, node: ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda):
        """push context"""
        # print(ast.dump(node))

        # names that should be defined in the parent scope
        if hasattr(node, "returns") and node.returns:
            self._handle_annotation(node.returns)

        if hasattr(node, "name"):
            self.real_names[node.name] = node

        # enter function scope
        self.push_ctx()
        args = node.args
        for arg in args.args:
            self.real_names[arg.arg] = arg
            if arg.annotation:
                self._handle_annotation(arg.annotation)
        if hasattr(args, "vararg") and args.vararg:
            self.real_names[args.vararg.arg] = args.vararg
        if hasattr(args, "kwarg") and args.kwarg:
            self.real_names[args.kwarg.arg] = args.kwarg

        self.generic_visit(node)

        # exit function scope
        self.pop_ctx()

    def _handle_annotation(self, annotation: ast.Attribute | ast.Constant):
        return_name = None
        if isinstance(annotation, ast.Attribute):
            return_name = flatten_attribute(annotation)
        elif isinstance(annotation, ast.Constant):
            return_name = annotation.value
        else:
            TypeError(f"Dont know how to handle annotation type: {ast.dump(annotation)}")

        if return_name is None:
            return

        name = Name.from_str(return_name)
        if not name.in_dict(self.real_names):
            self.fake_names.add(name)

    def visit_AsyncFunctionDef(self, node):
        """push context"""
        self.visit_FunctionDef(node)

    def visit_Lambda(self, node: ast.Lambda):
        self.visit_FunctionDef(node)

    def visit_ClassDef(self, node):
        """push context"""
        # print(ast.dump(node))
        self.real_names[node.name] = node
        self.push_ctx()
        self.generic_visit(node)
        self.pop_ctx()

    def visit_ListComp(self, node: ast.ListComp | ast.DictComp | ast.GeneratorExp | ast.SetComp):
        self.push_ctx()
        for gen in node.generators:
            if isinstance(gen.target, ast.Tuple):
                for name in gen.target.elts:
                    self.real_names[name.id] = name
            else:
                self.real_names[gen.target.id] = gen.target
        self.generic_visit(node)
        self.pop_ctx()
        # if isinstance(gen.iter, ast.Name):
        #     self.visit_Name(gen.iter)
        # elif isinstance(gen.iter, ast.Call):
        #     self.visit_Attribute(gen.iter.func)

    def visit_DictComp(self, node: ast.DictComp):
        self.visit_ListComp(node)

    def visit_GeneratorExp(self, node: ast.GeneratorExp):
        self.visit_ListComp(node)

    def visit_SetComp(self, node: ast.SetComp):
        self.visit_ListComp(node)

    def visit_For(self, node: ast.For):
        # for loops don't have scope, so we don't push/pop here
        # self.push_ctx()
        if isinstance(node.target, ast.Tuple):
            for name in node.target.elts:
                self.real_names[name.id] = name
        else:
            self.real_names[node.target.id] = node.target
        self.generic_visit(node)
        # self.pop_ctx()

    def visit_ExceptHandler(self, node: ast.ExceptHandler):
        self.push_ctx()
        if node.name:
            self.real_names[node.name] = node
        self.generic_visit(node)
        self.pop_ctx()

    def filter_fake_names(self):
        """
        After visiting, we remove top-level module level definitions from
        fake names, since it's possible to refer to things out of order in scopes
        """
        self.fake_names.names = [
            n for n in self.fake_names.names if n.module not in self.real_names
        ]

def parse_names(node: ast.AST) -> NameCollection:
    """
    Get the names that need to be imported from an AST module by applying
    :class:`.NameVisitor`
    """
    visitor = NameVisitor()
    visitor.visit(node)
    return visitor.fake_names



@overload
def generate_frontmatter(
    names: NameCollection, mode: Literal["ast"] = "ast"
) -> list[ast.Import | ast.Assign]: ...


@overload
def generate_frontmatter(names: NameCollection, mode: Literal["str"] = "str") -> str: ...


def generate_frontmatter(
    names: NameCollection, mode: Literal["ast", "str"] = "ast"
) -> list[ast.Import | ast.Assign] | str:

    if mode == "ast":
        return _frontmatter_ast(names)
    elif mode == "str":
        return _frontmatter_str(names)
    else:
        raise ValueError("Unknown frontmatter mode")


def _frontmatter_ast(names: NameCollection) -> list[ast.Import | ast.Assign]:
    modules = list(dict.fromkeys([name.module for name in names.names]))

    imports = [ast.Import(names=[ast.alias(name)]) for name in modules]
    assignments = []
    for name in names.names:
        for alias in name.aliases:
            assignments.append(
                ast.Assign(
                    targets=[ast.Name(id=alias, ctx=ast.Store())],
                    value=ast.Name(id=name.id, ctx=ast.Load()),
                )
            )

    return imports + assignments


def _frontmatter_str(names: NameCollection) -> str:
    modules = list(dict.fromkeys([name.module for name in names.names]))
    imports = [f"import {mod}" for mod in modules]

    assignments = []
    for name in names.names:
        for alias in name.aliases:
            assignments.append(f"{alias} = {name.id}")

    return "\n".join(imports + assignments)


def flatten_attribute(attr: ast.Attribute) -> str:
    if isinstance(attr.value, ast.Attribute):
        return ".".join([flatten_attribute(attr.value), attr.attr])
    elif isinstance(attr.value, ast.Name):
        return ".".join([attr.value.id, attr.attr])
    elif isinstance(attr.value, ast.Call):
        return attr.value.func.id
