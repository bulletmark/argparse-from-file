"""Tests for argparse_from_file."""

import io
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import platformdirs

import argparse_from_file as argparse
from argparse_from_file.argparse import _default_from_file, _split_args, _unexpanduser


class TestCase(unittest.TestCase):
    "Base test case with a temporary directory"

    def setUp(self):
        self._tempdir = tempfile.TemporaryDirectory()
        self.dir = Path(self._tempdir.name)
        self.addCleanup(self._tempdir.cleanup)

        # Keep the unittest command line out of the parsers under test.
        argv = mock.patch.object(sys, 'argv', ['prog'])
        argv.start()
        self.addCleanup(argv.stop)

    def write_conf(self, text, name='args.conf'):
        "Write a config file and return its path"
        path = self.dir / name
        path.write_text(text, encoding='utf-8')
        return str(path)

    def make_parser(self, conf, **kwargs):
        "Return a parser with a --foo int option"
        parser = argparse.ArgumentParser(from_file=conf, **kwargs)
        parser.add_argument('--foo', type=int, default=1)
        return parser


class TestFromFileName(TestCase):
    def test_default_names(self):
        self.assertEqual(_default_from_file('myprog'), 'myprog-flags.conf')
        self.assertEqual(_default_from_file('myprog.py'), 'myprog-flags.conf')
        self.assertEqual(
            _default_from_file('/usr/local/bin/myprog.py'), 'myprog-flags.conf'
        )

    def test_prog_with_path(self):
        target = self.dir / 'myprog-flags.conf'
        with mock.patch.object(
            platformdirs, 'user_config_path', return_value=target
        ) as user_config_path:
            parser = argparse.ArgumentParser(prog='/usr/local/bin/myprog.py')
        self.assertEqual(parser.from_file_path, target)
        user_config_path.assert_called_once_with('myprog-flags.conf', appauthor=False)

    def test_positional_prog(self):
        target = self.dir / 'myprog-flags.conf'
        with mock.patch.object(
            platformdirs, 'user_config_path', return_value=target
        ) as user_config_path:
            parser = argparse.ArgumentParser('myprog')
        self.assertEqual(parser.from_file_path, target)
        user_config_path.assert_called_once_with('myprog-flags.conf', appauthor=False)

    def test_absolute_from_file(self):
        conf = self.write_conf('')
        self.assertEqual(
            argparse.ArgumentParser(from_file=conf).from_file_path, Path(conf)
        )
        self.assertEqual(
            argparse.ArgumentParser(from_file=Path(conf)).from_file_path, Path(conf)
        )

    def test_disabled(self):
        parser = argparse.ArgumentParser(from_file='')
        self.assertIsNone(parser.from_file_path)
        self.assertIsNone(parser.epilog)
        # A later parser can still use a config file.
        conf = self.write_conf('--foo 7\n')
        self.assertEqual(self.make_parser(conf).parse_args().foo, 7)

    def test_subclass(self):
        conf = self.write_conf('--foo 7\n')

        class Parser(argparse.ArgumentParser):
            pass

        parser = Parser(from_file=conf)
        parser.add_argument('--foo', type=int, default=1)
        self.assertEqual(parser.parse_args().foo, 7)

    def test_failed_construction(self):
        conf = self.write_conf('--foo 7\n')
        with self.assertRaises(TypeError):
            argparse.ArgumentParser(from_file=conf, not_a_real_kwarg=True)
        self.assertEqual(self.make_parser(conf).parse_args().foo, 7)


class TestHelp(TestCase):
    def test_epilog_and_placeholders_positional(self):
        target = self.dir / 'myprog-flags.conf'
        with mock.patch.object(platformdirs, 'user_config_path', return_value=target):
            parser = argparse.ArgumentParser(
                'myprog',
                'usage #FROM_FILE_PATH#',
                'desc #FROM_FILE_PATH#',
                'epi #FROM_FILE_PATH#',
            )
        path = str(_unexpanduser(target))
        self.assertEqual(parser.prog, 'myprog')
        self.assertEqual(parser.usage, f'usage {path}')
        self.assertEqual(parser.description, f'desc {path}')
        self.assertEqual(parser.epilog, f'epi {path}')

    def test_default_epilog(self):
        target = self.dir / 'myprog-flags.conf'
        with mock.patch.object(platformdirs, 'user_config_path', return_value=target):
            parser = argparse.ArgumentParser('myprog')
        self.assertIn(str(_unexpanduser(target)), parser.epilog or '')

    def test_empty_epilog(self):
        conf = self.write_conf('')
        self.assertEqual(argparse.ArgumentParser(from_file=conf, epilog='').epilog, '')

    def test_remaining_positional_args(self):
        # parents and the other positional-or-keyword args must still bind.
        parent = argparse.ArgumentParser(add_help=False, from_file='')
        parent.add_argument('--parent-opt')
        parser = argparse.ArgumentParser(None, None, None, None, [parent], from_file='')
        parser.add_argument('--foo')
        ns = parser.parse_args(['--parent-opt', 'x', '--foo', 'y'])
        self.assertEqual((ns.parent_opt, ns.foo), ('x', 'y'))


class TestParse(TestCase):
    def test_parse_args(self):
        conf = self.write_conf('--foo 7\n')
        self.assertEqual(self.make_parser(conf).parse_args().foo, 7)

    def test_parse_known_args(self):
        conf = self.write_conf('--foo 7\n')
        self.assertEqual(self.make_parser(conf).parse_known_args()[0].foo, 7)

    def test_parse_intermixed_args(self):
        conf = self.write_conf('--foo 7\n')
        parser = self.make_parser(conf)
        parser.add_argument('--bar')
        with mock.patch.object(sys, 'argv', ['prog', '--bar', 'B']):
            ns = parser.parse_intermixed_args()
        self.assertEqual((ns.foo, ns.bar), (7, 'B'))

    def test_repeated_parse(self):
        conf = self.write_conf('--foo 7\n')
        parser = self.make_parser(conf)
        self.assertEqual(parser.parse_args().foo, 7)
        self.assertEqual(parser.parse_args().foo, 7)

    def test_explicit_args_ignore_file(self):
        conf = self.write_conf('--foo 7\n')
        parser = self.make_parser(conf)
        self.assertEqual(parser.parse_args([]).foo, 1)
        self.assertEqual(parser.parse_args([]).foo, 1)
        self.assertEqual(parser.parse_args(['--foo', '3']).foo, 3)
        self.assertEqual(parser.parse_args().foo, 7)

    def test_multiple_parsers(self):
        conf1 = self.write_conf('--foo 7\n', 'a.conf')
        conf2 = self.write_conf('--foo 9\n', 'b.conf')
        self.assertEqual(self.make_parser(conf1).parse_args().foo, 7)
        self.assertEqual(self.make_parser(conf2).parse_args().foo, 9)

    def test_parents(self):
        conf = self.write_conf('--foo 7\n')
        missing = self.dir / 'missing.conf'
        with mock.patch.object(platformdirs, 'user_config_path', return_value=missing):
            parent = argparse.ArgumentParser(add_help=False)
        parent.add_argument('--parent-opt', default='x')
        parser = argparse.ArgumentParser(parents=[parent], from_file=conf)
        parser.add_argument('--foo', type=int, default=1)
        self.assertEqual(parser.parse_args().foo, 7)

    def test_subparsers(self):
        conf = self.write_conf('--foo 7\n')
        parser = self.make_parser(conf)
        sub = parser.add_subparsers(dest='cmd')
        run = sub.add_parser('run')
        run.add_argument('--bar')
        self.assertIsNone(run.from_file_path)
        self.assertIsNone(run.epilog)
        with mock.patch.object(sys, 'argv', ['prog', 'run', '--bar', 'B']):
            ns = parser.parse_args()
        self.assertEqual((ns.foo, ns.cmd, ns.bar), (7, 'run', 'B'))

    def test_subparser_explicit_from_file(self):
        main_conf = self.write_conf('', 'main.conf')
        sub_conf = self.write_conf('--foo 9\n', 'sub.conf')
        parser = argparse.ArgumentParser(from_file=main_conf)
        sub = parser.add_subparsers()
        run = sub.add_parser('run', from_file=sub_conf)
        run.add_argument('--foo', type=int, default=1)
        self.assertEqual(run.from_file_path, Path(sub_conf))
        self.assertEqual(run.parse_args().foo, 9)


class TestFromFileOnly(TestCase):
    def test_file_used(self):
        conf = self.write_conf('--foo 7\n')
        parser = self.make_parser(conf, from_file_only=True)
        with mock.patch.object(sys, 'argv', ['prog', '--foo', '5']):
            self.assertEqual(parser.parse_args().foo, 7)

    def test_explicit_args_ignored(self):
        conf = self.write_conf('--foo 7\n')
        parser = self.make_parser(conf, from_file_only=True)
        self.assertEqual(parser.parse_args(['--foo', '6']).foo, 7)

    def test_missing_file_ignores_cli(self):
        conf = str(self.dir / 'missing.conf')
        parser = self.make_parser(conf, from_file_only=True)
        with mock.patch.object(sys, 'argv', ['prog', '--foo', '5']):
            self.assertEqual(parser.parse_args().foo, 1)

    def test_intermixed(self):
        conf = self.write_conf('--foo 7\n')
        parser = self.make_parser(conf, from_file_only=True)
        parser.add_argument('--bar')
        with mock.patch.object(sys, 'argv', ['prog', '--bar', 'B']):
            ns = parser.parse_intermixed_args()
        self.assertEqual((ns.foo, ns.bar), (7, None))


class TestConfigFile(TestCase):
    def test_utf8_bom(self):
        path = self.dir / 'bom.conf'
        path.write_bytes(b'\xef\xbb\xbf--foo 7\n')
        self.assertEqual(self.make_parser(str(path)).parse_args().foo, 7)

    def test_utf8_value(self):
        path = self.dir / 'utf8.conf'
        path.write_text('--name h\u00e9llo\n', encoding='utf-8')
        parser = argparse.ArgumentParser(from_file=str(path))
        parser.add_argument('--name')
        self.assertEqual(parser.parse_args().name, 'h\u00e9llo')

    def test_windows_paths(self):
        with mock.patch.object(os, 'name', 'nt'):
            args = _split_args([r'--path C:\temp\new', '--name "two words"'])
        self.assertEqual(args, ['--path', r'C:\temp\new', '--name', 'two words'])

    def test_bad_quoting(self):
        conf = self.write_conf('--foo "unterminated\n')
        parser = self.make_parser(conf)
        stderr = io.StringIO()
        with mock.patch.object(sys, 'stderr', stderr), self.assertRaises(SystemExit):
            parser.parse_args()
        self.assertIn('cannot parse args from', stderr.getvalue())

    @unittest.skipIf(os.name == 'nt', 'POSIX file permissions required')
    def test_unreadable_file_warns(self):
        if os.geteuid() == 0:
            self.skipTest('root can read any file')
        conf = self.write_conf('--foo 7\n')
        os.chmod(conf, 0)
        self.addCleanup(os.chmod, conf, 0o600)
        with self.assertWarns(UserWarning):
            parser = self.make_parser(conf)
        self.assertEqual(parser.parse_args([]).foo, 1)


if __name__ == '__main__':
    unittest.main()
