# ARGPARSE-FROM-FILE
[![PyPi](https://img.shields.io/pypi/v/argparse-from-file)](https://pypi.org/project/argparse-from-file/)
[![AUR](https://img.shields.io/aur/version/python-argparse-from-file)](https://aur.archlinux.org/packages/python-argparse-from-file/)

`argparse-from-file` is a lightweight wrapper for Python's standard
[`argparse`][argparse] module. It allows your program to read default arguments
from a configuration file, which are prepended to arguments provided on the
command line.

The latest version of this document and code is available at
https://github.com/bulletmark/argparse-from-file.

## Features

* **Drop-in replacement:** Simply change `import argparse` to `import
  argparse_from_file as argparse`. No other code changes are needed for basic
  functionality.
* **Automatic configuration:** By default, it loads arguments from
  `<program_name>-flags.conf` in the user's configuration directory (e.g.,
  `~/.config/` on Linux). The exact path is determined using the
  [`platformdirs`][platformdirs] library to respect OS conventions.
* **Custom configuration file:** Specify a custom file path with the
  `from_file` argument to [`ArgumentParser()`][argparser].
* **Simple file format:** The configuration file is a simple text file with
  options specified on one or more lines. Blank lines and lines starting with
  `#` are ignored.
* **Informative help text:** The program's help message is automatically
  updated to show the path to the configuration file.

## Usage

To get started, replace the standard [`argparse`][argparse] import in your project:

```python
# import argparse
import argparse_from_file as argparse
```

That's it! Your application will now automatically look for a default
configuration file and use the default arguments provided therein.

To specify a custom configuration file, use the `from_file` keyword argument,
which is the only addition to the standard
[`ArgumentParser()`][argparser] API:

```python
# Use a specific () file path
parser = argparse.ArgumentParser(from_file='/path/to/myprog.conf', ..)

# Use a file relative to the user's config directory
parser = argparse.ArgumentParser(from_file='myprog.conf', ..)
```

The `from_file` argument accepts a string or a [`pathlib.Path`][pathlib].
Relative paths are resolved relative to the user's configuration directory as
determined by `platformdirs`.

## Configuration File Format

Arguments in the configuration file are best specified one per line so they can
easily be commented out. It is also recommended to use long-form options for
clarity.

Example `~/.config/myprog-flags.conf`:
```
# Always run with foo set to 123
--foo 123

# Default to verbose output
--verbose
```

## Customizing the Help Message

`argparse-from-file` automatically adds an `epilog` to the help message
indicating the configuration file path. If you instead provide a custom `epilog`
(or `usage` or `description`), you can embed a `#FROM_FILE_PATH#` placeholder,
and it will be replaced with the actual path used.

## Example

Here is a simple example program (`myprog.py`):

```python
#!/usr/bin/python3
import argparse_from_file as argparse

parser = argparse.ArgumentParser()
parser.add_argument('--foo', type=int, default=42, help='foo help')
opts = parser.parse_args()

print(f"foo is: {opts.foo}")
```

If `~/.config/myprog-flags.conf` contains `--foo=123`, the output is:

```
$ python myprog.py
foo is: 123
```

The help text (`epilog`) is also automatically added as seen below:
```
$ python myprog.py -h
usage: myprog.py [-h] [--foo FOO]

options:
  -h, --help  show this help message and exit
  --foo FOO   foo help

Note you can set default starting options in /home/user/.config/myprog-flags.conf.
```

## Installation

Arch Linux users can install `python-argparse-from-file` from the
[AUR](https://aur.archlinux.org/packages/python-argparse-from-file/).

Alternatively, `argparse-from-file` is available on
[PyPI](https://pypi.org/project/argparse-from-file/) and can be installed with
pip:

```bash
pip install argparse-from-file
```

## License

Copyright (C) 2025 Mark Blakeney. This program is distributed under the terms
of the GNU General Public License. This program is free software: you can
redistribute it and/or modify it under the terms of the GNU General Public
License as published by the Free Software Foundation, either version 3 of the
License, or any later version. This program is distributed in the hope that it
will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public
License at <https://opensource.org/license/gpl-3-0> for more details.

[argparse]: https://docs.python.org/3/library/argparse.html
[platformdirs]: https://github.com/tox-dev/platformdirs
[argparser]: https://docs.python.org/3/library/argparse.html#argumentparser-objects
[pathlib]: https://docs.python.org/3/library/pathlib.html
<!-- vim: se ai syn=markdown: -->
