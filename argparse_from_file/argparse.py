"""
A very light wrapper around Python's argparse module to prepend a program's
argument list with default options and arguments read from a user configuration
file.
"""

from __future__ import annotations

import argparse
import os
import shlex
import sys
import warnings
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

import platformdirs

PLACEHOLDER = '#FROM_FILE_PATH#'


def _default_from_file(prog: str | None) -> str:
    "Return default config file name for the program"
    if not prog:
        try:
            modspec = sys.modules['__main__'].__spec__
        except (KeyError, AttributeError):
            # possibly PYTHONSTARTUP or -X presite or other weird edge case
            # no good answer here, so fall back to the default
            modspec = None

        if not modspec or (name := modspec.name) == '__main__':
            prog = Path(sys.argv[0]).name
        else:
            prog = name[:-9] if name.endswith('.__main__') else name

    name = Path(prog).name
    return (name[:-3] if name.endswith('.py') else name) + '-flags.conf'


def _unexpanduser(path: Path) -> Path:
    "Return path name, with $HOME replaced by ~, i.e. opposite of Path.expanduser() for current user"
    startlen = len(hparts := path.home().parts)
    parts = path.parts
    if parts[:startlen] == hparts:
        path = Path('~', *parts[startlen:])

    return path


def _split_args(lines: Sequence[str]) -> list[str]:
    "Return list of arguments from the lines of a configuration file"
    argstr = ' '.join(lines)

    if os.name != 'nt':
        return shlex.split(argstr)

    # POSIX mode would treat the backslashes in Windows paths, e.g.
    # C:\temp, as escape characters, so split in non-POSIX mode instead.
    # That mode leaves any quotes on the returned tokens, so remove them.
    return [
        token[1:-1]
        if len(token) > 1 and token[0] == token[-1] and token[0] in ('"', "'")
        else token
        for token in shlex.split(argstr, posix=False)
    ]


class ArgumentParser(argparse.ArgumentParser):
    def __init__(
        self,
        prog: str | None = None,
        usage: str | None = None,
        description: str | None = None,
        epilog: str | None = None,
        *args: Any,
        from_file: str | Path | None = None,
        from_file_only: bool = False,
        **kwargs: Any,
    ) -> None:
        self.from_file_path: Path | None = None
        self._argv_from_file: list[str] = []
        self._from_file_only = from_file_only
        self._parsing = False

        # from_file = None: Create default "from file" path.
        # from_file = 'path-to/file': Use this as "from file" name/path. If
        #   relative then wrt platform specific user config dir.
        # from_file = '': Do not use a "from file".
        if from_file is None:
            from_file = _default_from_file(prog)

        if from_file:
            self.from_file_path = Path(from_file).expanduser()
            if not self.from_file_path.is_absolute():
                self.from_file_path = platformdirs.user_config_path(
                    str(from_file), appauthor=False
                )

            from_file_str = str(_unexpanduser(self.from_file_path))

            # epilog = None: create default epilog with "from file" path.
            # epilog = 'text string': Set this as epilog, replacing any
            #   PLACEHOLDER with the above determined "from file" path.
            # epilog = '': Do not set an epilog.
            if epilog is None:
                epilog = (
                    f'Note you can set default starting options in {from_file_str}.'
                )
            else:
                epilog = epilog.replace(PLACEHOLDER, from_file_str)

            # Also replace PLACEHOLDER in usage and description.
            if usage:
                usage = usage.replace(PLACEHOLDER, from_file_str)
            if description:
                description = description.replace(PLACEHOLDER, from_file_str)

            # Create list of default args from user file.
            try:
                with self.from_file_path.open(encoding='utf-8-sig') as fp:
                    self._argv_from_file = [
                        ln
                        for line in fp
                        if (ln := line.strip()) and not ln.startswith('#')
                    ]
            except FileNotFoundError:
                pass
            except (OSError, UnicodeDecodeError) as err:
                warnings.warn(f'Cannot read {from_file_str}: {err}', stacklevel=2)

        super().__init__(prog, usage, description, epilog, *args, **kwargs)

    def add_subparsers(self, **kwargs: Any) -> Any:
        # Sub-parsers must not also read the "from file" args, only this, the
        # main, parser does that.
        parser_class = kwargs.get('parser_class') or type(self)
        if isinstance(parser_class, type) and issubclass(parser_class, ArgumentParser):

            def factory(**sub_kwargs: Any) -> argparse.ArgumentParser:
                # "From file" options apply to the main parser only. A
                # sub-parser gets its args from the main parser, so must never
                # ignore them.
                sub_kwargs.setdefault('from_file', '')
                sub_kwargs['from_file_only'] = False
                return parser_class(**sub_kwargs)

            kwargs['parser_class'] = factory

        return super().add_subparsers(**kwargs)

    def _merge_args(self, args: Iterable[str] | None) -> Iterable[str] | None:
        "Return args to parse, with any args from the file applied"
        if not self._from_file_only and args is not None:
            # Explicitly passed args take precedence over the file args.
            return args

        try:
            file_args = _split_args(self._argv_from_file)
        except ValueError as err:
            self.error(f'cannot parse args from {self.from_file_path}: {err}')

        # In "from file only" mode the command line is ignored entirely.
        return file_args if self._from_file_only else file_args + sys.argv[1:]

    def parse_known_args(
        self,
        args: Iterable[str] | None = None,
        namespace: Any = None,
    ) -> tuple[Any, list[str]]:
        if self._parsing:
            # An internal call from argparse, so use the args as given.
            return super().parse_known_args(args, namespace)

        try:
            self._parsing = True
            return super().parse_known_args(self._merge_args(args), namespace)
        finally:
            self._parsing = False

    def parse_known_intermixed_args(
        self,
        args: Iterable[str] | None = None,
        namespace: Any = None,
    ) -> tuple[Any, list[str]]:
        if self._parsing:
            return super().parse_known_intermixed_args(args, namespace)

        try:
            self._parsing = True
            return super().parse_known_intermixed_args(
                self._merge_args(args), namespace
            )
        finally:
            self._parsing = False
