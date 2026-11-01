"""Exercise the real website checker from outside its source directory."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class RepositoryLayoutTest(unittest.TestCase):
    def test_live_source_checker_runs_from_unrelated_cwd(self):
        repository = next(p for p in Path(__file__).resolve().parents
                          if (p / '.github/workflows/pages.yml').is_file())
        website = repository / 'website'
        checker = website / 'tools/check_content.py'
        self.assertTrue(checker.is_file(), 'Website tools must live under website/')
        with tempfile.TemporaryDirectory(dir=website / 'tests', prefix='.layout-check-') as unrelated:
            result = subprocess.run([sys.executable, str(checker), '--json'], cwd=unrelated,
                                    capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(json.loads(result.stdout)['ok'])


if __name__ == '__main__':
    unittest.main()
