"""
A very light wrapper around Python's argparse module to prepend a program's
argument list with default options and arguments read from a user configuration
file.
"""

import argparse
import os
import shlex
import sys

import platformdirs

PLACEHOLDER = '#FROM_FILE_PATH#'


# Get program name. This function is copied (but very modified) from argparse 3.14.0
def _prog_name() -> str:
    try:
        modspec = sys.modules['__main__'].__spec__
    except (KeyError, AttributeError):
        # possibly PYTHONSTARTUP or -X presite or other weird edge case
        # no good answer here, so fall back to the default
        modspec = None

    if not modspec or (name := modspec.name) == '__main__':
        return os.path.basename(sys.argv[0])

    return name[:-9] if name.endswith('.__main__') else name


class ArgumentParser(argparse.ArgumentParser):
    _top = True

    def __init__(self, *args, **kwargs):
        self._argv = []

        # Only set up "from file" stuff once, for the top-level/main ArgumentParser()
        if __class__._top:
            __class__._top = False

            # from_file = 'path-to/file': Use this as "from file" name/path. If
            #   relative then wrt platform specific user config dir.
            # from_file = '': Do not use a "from file".
            # from_file = None: Create default "from file" path.
            if (from_file := kwargs.pop('from_file', None)) is None:
                from_file = _prog_name() + '-flags.conf'

            if from_file:
                from_file_path = platformdirs.user_config_path(from_file)
                from_file_path_str = str(from_file_path)
                # epilog = 'text string': Set this as epilog, replacing any
                #   PLACEHOLDER with the above determined "from file" path.
                # epilog = '': Do not set an epilog.
                # epilog = None: create default epilog with "from file" path.
                if (epilog := kwargs.pop('epilog', None)) is None:
                    epilog = f'Note you can set default starting options in {from_file_path_str}.'
                else:
                    epilog = epilog.replace(PLACEHOLDER, from_file_path_str)

                if epilog:
                    kwargs['epilog'] = epilog

                # Also replace PLACEHOLDER in usage and description.
                for kw in 'usage', 'description':
                    if v := kwargs.get(kw):
                        kwargs[kw] = v.replace(PLACEHOLDER, from_file_path_str)

                # Create list of default args from user file.
                if from_file_path.is_file():
                    with from_file_path.open() as fp:
                        self._argv.extend(
                            ln
                            for line in fp
                            if (ln := line.strip()) and not ln.startswith('#')
                        )
            else:
                from_file_path = None

            self.from_file_path = from_file_path

        super().__init__(*args, **kwargs)

    def parse_args(self, args=None, namespace=None):  # type: ignore[override]
        if args is None and self._argv:
            # Combine args from file and command line, to be parsed
            argstr = ' '.join(self._argv).strip()
            args = shlex.split(argstr) + sys.argv[1:]
            self._argv.clear()

        return super().parse_args(args, namespace)
