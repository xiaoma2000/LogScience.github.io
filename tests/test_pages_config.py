"""Protect local preview and both Pages URL shapes."""
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'tools' / 'prepare_pages_config.py'
SPEC = importlib.util.spec_from_file_location('pages_config', SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class PagesConfigTests(unittest.TestCase):
    source = '# Preserve comments\nurl : "https://yilouisliu.github.io"\nbaseurl :\nrepository :\nauthor:\n  url: "https://profile.example/"\n'

    def test_student_project_path_and_nested_values(self):
        value = MODULE.prepare_config(self.source, 'https://xiaoma2000.github.io',
                                      '/LogScience.github.io', 'xiaoma2000/LogScience.github.io')
        self.assertIn('url: "https://xiaoma2000.github.io"', value)
        self.assertIn('baseurl: "/LogScience.github.io"', value)
        self.assertIn('repository: "xiaoma2000/LogScience.github.io"', value)
        self.assertIn('  url: "https://profile.example/"', value)
        self.assertTrue(value.startswith('# Preserve comments'))

    def test_pi_root_domain_uses_empty_base_path(self):
        value = MODULE.prepare_config(self.source, 'https://yilouisliu.github.io', '',
                                      'YiLouisLIU/YiLouisLIU.github.io')
        self.assertIn('baseurl: ""', value)
        self.assertIn('repository: "YiLouisLIU/YiLouisLIU.github.io"', value)

    def test_missing_root_keys_are_added(self):
        value = MODULE.prepare_config('title: Lab\n', 'https://example.github.io', '', 'example/site')
        self.assertIn('title: Lab\n', value)
        self.assertIn('url: "https://example.github.io"', value)

    def test_invalid_origin_is_rejected(self):
        for origin in ['http://example.github.io', 'https://example.github.io/path',
                       'https://user:secret@example.github.io', 'https://example.github.io?q=1']:
            with self.subTest(origin=origin), self.assertRaises(ValueError):
                MODULE.prepare_config(self.source, origin, '', 'example/site')

    def test_unsafe_base_paths_are_rejected(self):
        for path in ['site', '//elsewhere', '/../site', '/site?mode=1', '/site#x', '/site name']:
            with self.subTest(path=path), self.assertRaises(ValueError):
                MODULE.prepare_config(self.source, 'https://example.github.io', path, 'example/site')

    def test_repository_must_be_owner_and_name(self):
        for repository in ['site', 'owner/site/extra', 'owner/site\nurl: bad']:
            with self.subTest(repository=repository), self.assertRaises(ValueError):
                MODULE.prepare_config(self.source, 'https://example.github.io', '', repository)

    def test_default_config_is_never_changed_outside_actions(self):
        original = SCRIPT.parents[1] / '_config.yml'
        before = original.read_bytes()
        environment = dict(os.environ, PAGES_ORIGIN='https://example.github.io',
                           PAGES_BASE_PATH='/site', PAGES_REPOSITORY='example/site')
        environment.pop('GITHUB_ACTIONS', None)
        result = subprocess.run([sys.executable, str(SCRIPT)], env=environment,
                                capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Refusing to change the local site config', result.stderr)
        self.assertEqual(original.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
