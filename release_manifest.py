"""Allowlisted public source and in-place update files.

Explicit lists intentionally prevent downloaded media, local config and secrets
from entering GitHub uploads or release ZIPs. Add new files deliberately.
"""
from __future__ import annotations

# Minimal source-installation update: do not ship test suites, build artifacts,
# maintainer guides or GitHub metadata into the user's installed app folder.
APP_FILES = (
    'studio_core.py',
    'download_runtime.py',
    'pinterest_studio.py',
    'ui_theme.py',
    'ui_qt.py',
    'ui_language.py',
    'requirements.txt',
    'app_icon.png',
    'app_icon.ico',
    'Run on Windows.bat',
    'Update Engines.bat',
    'Build EXE (Windows).bat',
    'upgrade_existing.py',
    'Upgrade Existing Installation.bat',
    'Rollback Last Update.bat',
    'release_manifest.py',
    'tools/bootstrap.py',
    'README.md',
    'README-FA.md',
    'CHANGELOG.md',
    'CHANGELOG-FA.md',
    'THIRD-PARTY.md',
    'NOTICE.md',
    'LICENSE',
    'docs/INSTALL-EN.md',
    'docs/INSTALL-FA.md',
    'docs/TROUBLESHOOTING-EN.md',
    'docs/TROUBLESHOOTING-FA.md',
)

PUBLIC_ONLY_FILES = (
    '.gitattributes',
    '.gitignore',
    '.github/workflows/ci.yml',
    '.github/PULL_REQUEST_TEMPLATE.md',
    '.github/ISSUE_TEMPLATE/bug_report.yml',
    '.github/ISSUE_TEMPLATE/feature_request.yml',
    'assets/pinharbor-banner.png',
    'assets/pinharbor-icon-256.png',
    'CONTRIBUTING.md',
    'CODE_OF_CONDUCT.md',
    'SECURITY.md',
    'SUPPORT.md',
    'ROADMAP.md',
    'docs/PRIVACY-EN.md',
    'docs/PRIVACY-FA.md',
    'docs/MAINTAINER-EN.md',
    'docs/MAINTAINER-FA.md',
    'docs/RELEASE-CHECKLIST.md',
    'Publish to GitHub.bat',
    'tools/github_publish.py',
    'tools/build_release.py',
    'tools/verify_repository.py',
    'tools/smoke_gui.py',
    'tools/collect_licenses.py',
    'tests/test_core.py',
    'tests/test_engine_mode.py',
    'tests/test_features_22.py',
    'tests/test_quality_25.py',
    'tests/test_regressions.py',
    'tests/test_release_24.py',
    'tests/test_repo_hygiene.py',
    'tests/test_theme_23.py',
    'tests/test_upgrade.py',
    'tests/test_coverage_26.py',
)

SOURCE_FILES = tuple(dict.fromkeys((*APP_FILES, *PUBLIC_ONLY_FILES)))

# Only paths that existed in generated v2.5.0 bundles are eligible for
# automatic untracking. NEVER remove arbitrary user files or unknown paths.
OBSOLETE_TRACKED_FILES = (
    'README-EN.md',
    'START-HERE.txt',
    'docs/GITHUB-PUBLISH-FA.md',
    'docs/ONE-CLICK-PUBLISH-EN.md',
    'docs/ONE-CLICK-PUBLISH-FA.md',
    'docs/LAUNCH-KIT-FA-EN.md',
    'docs/QA-REPORT.md',
    'docs/BRAND-GUIDE.md',
    'docs/RELEASE-NOTES-EN.md',
    'docs/RELEASE-NOTES-FA.md',
    'assets/pinharbor-icon-512.png',
    'assets/pinharbor-icon.ico',
)
