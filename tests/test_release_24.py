"""Release packaging, documentation and in-place migration contract tests."""
from pathlib import Path
import ast
import unittest

from studio_core import APP_NAME, APP_VERSION
from upgrade_existing import APP_FILES

R = Path(__file__).resolve().parents[1]


class PublicReleaseTests(unittest.TestCase):
    def test_brand_and_release_version(self):
        self.assertEqual(APP_VERSION, '2.5.0')
        self.assertEqual(APP_NAME, 'PinHarbor')

    def test_qsettings_preserved_for_legacy_users(self):
        content = (R / 'pinterest_studio.py').read_text(encoding='utf8')
        self.assertIn('QSettings("PinterestBoardStudio", "Desktop")', content)
        self.assertIn('heading = QLabel("PinHarbor")', content)

    def test_all_update_files_exist(self):
        missing = [f for f in APP_FILES if not (R / f).is_file()]
        self.assertEqual(missing, [])

    def test_public_documentation_present(self):
        files = ['README.md','README-FA.md','README-EN.md','LICENSE',
                 'CONTRIBUTING.md','SUPPORT.md','SECURITY.md','CODE_OF_CONDUCT.md',
                 'docs/INSTALL-EN.md','docs/INSTALL-FA.md',
                 'docs/PRIVACY-EN.md','docs/PRIVACY-FA.md',
                 'docs/RELEASE-CHECKLIST.md','docs/GITHUB-PUBLISH-FA.md',
                 '.github/ISSUE_TEMPLATE/bug_report.yml',
                 '.github/ISSUE_TEMPLATE/feature_request.yml']
        for file in files:
            with self.subTest(file=file):
                self.assertTrue((R / file).is_file())

    def test_syntax(self):
        for f in ['studio_core.py','pinterest_studio.py','upgrade_existing.py',
                  'download_runtime.py','ui_theme.py','tools/build_release.py']:
            with self.subTest(file=f):
                ast.parse((R / f).read_text(encoding='utf8'))


if __name__ == '__main__':
    unittest.main()
