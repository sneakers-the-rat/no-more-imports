# no-more-imports

python with no imports

*"hell ya it's got side effects"*

## Pitch

Do YOU have an unbounded hostility for others including your future self?

Do YOU hate code that can be understood and run?

Do YOU hate typing the word `import`?

Then `no-more-imports` might be right for YOU.

Simply import `no_more_imports`, and you'll never need another import again!

```python
import no_more_imports

# just use it baby nobody's watching!
re.search('hell ya', 'can i get a hell ya')

def eff_it(x=1):
    # you bet it'll install packages if you don't have them
    generator = numpy.random.default_rng()
    data = generator.random((100, 100))

# forgot where something comes from? no problem, just live your life
data = default_rng().random((10,10))
```

## Installation

```shell
pip install no-more-imports 
```

## "Features"

- Import it once in an interpreter session, it'll lazify everything else.
  That's right - import it at the root of your package and that's a single import for the entire package!
- Patch the currently importing module! no need to put code in another module
  like some [*other*](https://github.com/aroberge/ideas) dynamic AST rewriting packages
- You only need to use the fully qualified module name once,
  afterwards, just use the name of the function or class
- Dodges your other, regular names and doesn't try to import every variable in the world
- Tries to install missing packages if they aren't already! The height of convenience!

## Usage

Do not use this package

## How it Works

Well buster, i gotta say that's a little nosy, but if you must know,
on import, we take over the import system and inject a bunch of code!

Specifically, we interrupt the part of the import process where the source code is read,
and instead of leaving it alone, we fiddle around with it. 

First we parse it into an AST tree and try and find any names that are unbound.
We mimic python's scope, so we don't try and import any variables that are actually declared.
If we find references to a name that may have already been used before,
like `match()` being used after `re.match()`, we stash those as aliases that
we need to create.

After finding names, we generate some frontmatter that gets injected at the start of the file.
This handles imports and also assigns the abbreviated name.

The example above is actually this!

```python
import re
import numpy.random
default_rng = numpy.random.default_rng
import no_more_imports

# just use it baby nobody's watching!
re.search('hell ya', 'can i get a hell ya')

def eff_it(x=1):
    # you bet it'll install packages if you don't have them
    generator = numpy.random.default_rng()
    data = generator.random((100, 100))

# forgot where something comes from? no problem, just live your life
data = default_rng().random((10,10))
```

To be able to do that in the importing frame, rather than just any imports
that happen afterwards, on import we intercept the calling frame,
inspect its source code for unbound names,
and execute that extra frontmattter segment in the context of the calling frame!

No fuss! All bugs!

## Caveats

- I already told you to not use this package
- You can't lazily refer to names in the importing module
  *at the module level* - the check for unbound names happens before
  imports happen, so there's nothing we can do. 
  You *can* use unbound names at the module level in any module
  that's imported *after* the first module that imports `no_more_imports` since
  after that point we own the import machinery :)
