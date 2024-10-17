import inspect
import pdb
import sys
import ast
from typing import Optional
from types import ModuleType
import os
from importlib.abc import MetaPathFinder, Loader, SourceLoader, FileLoader
from importlib.machinery import FileFinder
from importlib import invalidate_caches
from importlib.machinery import ModuleSpec, SourceFileLoader
import importlib.util
from importlib.util import spec_from_file_location


from lazy_import.ast import NameVisitor, generate_frontmatter


class LazyLoader(FileLoader, SourceLoader):
    """
    Try to import any names that are referenced without imports

    Thx to https://stackoverflow.com/a/43573798/13113166 for the clear example
    """

    def get_data(self, path) -> str | None:
        """
        Modify the source code to include imports and assignments to make
        lazy imports work.

        Do it this way rather than using `source_to_code` because
        this way we still get meaningful error messages that can show
        the source lines that are failing
        """
        with open(path) as f:
            data = f.read()

        if self.name.split('.')[0] in sys.stdlib_module_names:
            return data

        parsed = ast.parse(data)
        frontmatter = generate_frontmatter(parsed)

        # put the frontmatter first and replace
        frontmatter.extend(parsed.body)
        parsed.body = frontmatter

        # fix after modifying and return to string
        parsed = ast.fix_missing_locations(parsed)
        deparsed = ast.unparse(parsed)
        return deparsed

class LazyFinder(MetaPathFinder):
    def find_spec(self, fullname, path, target=None):
        if path is None or path == "":
            path = [os.getcwd()] # top level import --

        if fullname.split('.')[0] in sys.builtin_module_names:
            return None

        if "." in fullname:
            *parents, name = fullname.split(".")
        else:
            name = fullname

        for entry in path:
            if os.path.isdir(os.path.join(entry, name)):
                # this module has child modules
                filename = os.path.join(entry, name, "__init__.py")
                submodule_locations = [os.path.join(entry, name)]
            else:
                filename = os.path.join(entry, name + ".py")
                submodule_locations = None
            if not os.path.exists(filename):
                continue

            return spec_from_file_location(fullname, filename, loader=LazyLoader(fullname, filename),
                submodule_search_locations=submodule_locations)

        return None # we don't know how to import this

def patch_importing_frame():
    """
    Inject needed imports into the importing frame as well :)
    """
    current_frame = inspect.currentframe()
    outer_frames = inspect.getouterframes(current_frame, context=3)
    importing_frame = outer_frames[-1].frame

    try:
        source = inspect.getsource(importing_frame)
    except OSError:
        # stdin, compiled extensions, etc.
        return

    node = ast.parse(source)
    frontmatter = generate_frontmatter(node, mode='str')
    exec(frontmatter, importing_frame.f_globals, importing_frame.f_locals)



def install():
    patch_importing_frame()
    sys.meta_path.insert(0, LazyFinder())
