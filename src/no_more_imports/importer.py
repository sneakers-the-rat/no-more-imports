import ast
import inspect
import os
import subprocess
import sys
from importlib.abc import FileLoader, MetaPathFinder, SourceLoader
from importlib.util import find_spec, spec_from_file_location
from pprint import pformat

from no_more_imports.ast import NameCollection, generate_frontmatter, parse_names
from no_more_imports.const import HARDCODED_SKIPS


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

        base_name = self.name.split(".")[0]
        if base_name in sys.stdlib_module_names or base_name in HARDCODED_SKIPS:
            return data

        parsed = ast.parse(data)
        names = parse_names(parsed)
        install_packages(names)
        frontmatter = generate_frontmatter(names)

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
            path = [os.getcwd()]  # top level import --

        base_name = fullname.split(".")[0]
        if base_name in sys.stdlib_module_names or base_name in HARDCODED_SKIPS:
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

            return spec_from_file_location(
                fullname,
                filename,
                loader=LazyLoader(fullname, filename),
                submodule_search_locations=submodule_locations,
            )

        return None  # we don't know how to import this


def patch_importing_frame():
    """
    Inject needed imports into the importing frame as well :)
    """
    current_frame = inspect.currentframe()
    outer_frames = inspect.getouterframes(current_frame, context=1)
    importing_frame = outer_frames[-1].frame
    try:
        source = inspect.getsource(importing_frame)
    except OSError:
        # stdin, compiled extensions, etc.
        return

    node = ast.parse(source)
    names = parse_names(node)
    install_packages(names)
    frontmatter = generate_frontmatter(names, mode="str")
    exec(frontmatter, importing_frame.f_globals, importing_frame.f_locals)


def install_packages(names: NameCollection):
    """
    Try to install any packages we can't import!
    """
    quiet = bool(os.environ.get('NMI_QUIET', False))
    to_install = []
    for name in names:
        base_module = name.module.split('.')[0]
        if base_module in sys.stdlib_module_names or base_module in sys.builtin_module_names:
            continue
        do_install = False
        try:
            spec = find_spec(base_module)
            if spec is None:
                do_install = True
        except ModuleNotFoundError:
            do_install = True

        if do_install:
            to_install.append(base_module)

    if not to_install:
        return

    _do_install(to_install, quiet)


def _do_install(packages: list[str], quiet: bool = False):
    if len(packages) == 0:
        return
    if not quiet:
        print(f"we're gonna try to install some stuff:\n    {packages}")

    errors = []
    for package in packages:
        res = subprocess.run(['python', '-m', 'pip', 'install', package], capture_output=True)
        if res.returncode != 0:
            errors.append({'package': package, 'stdout': res.stdout, 'stderr': res.stderr})
    if len(errors) == 0:
        print("sweet jesus we did it")
    else:
        print(f"some problems here pal:\n{pformat(errors, indent=2, compact=True)}")


def install():
    patch_importing_frame()
    sys.meta_path.insert(0, LazyFinder())
