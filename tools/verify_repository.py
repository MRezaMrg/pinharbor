"""Validate that only intentional files are eligible for GitHub and releases."""
from __future__ import annotations
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from release_manifest import APP_FILES, SOURCE_FILES, OBSOLETE_TRACKED_FILES  # noqa: E402


def audit_repository(root: Path = ROOT) -> list[str]:
    issues: list[str] = []
    sources = set(SOURCE_FILES)
    if len(sources) != len(SOURCE_FILES):
        issues.append('Duplicate paths in SOURCE_FILES')
    if len(set(APP_FILES)) != len(APP_FILES):
        issues.append('Duplicate paths in APP_FILES')
    if not set(APP_FILES) <= sources:
        issues.append('Update file missing from source allowlist')
    if sources & set(OBSOLETE_TRACKED_FILES):
        issues.append('Legacy files still included in source allowlist')
    for name in sources:
        p = Path(name)
        if p.is_absolute() or not p.parts or any(part in {'.', '..'} for part in p.parts):
            issues.append(f'Unsafe source path: {name}')
            continue
        path = root / name
        if not path.is_file() or path.is_symlink():
            issues.append(f'Missing or unsafe source file: {name}')
        if any(part in {'__pycache__', 'release', '.git', '.pinterest-studio', 'dist', 'build'} for part in p.parts):
            issues.append(f'Generated/private source file selected: {name}')
        if p.suffix in {'.db', '.sqlite3', '.pyc', '.zip'}:
            issues.append(f'Non-source artifact selected: {name}')
    expected = set()
    for folder in (root, root / 'tests', root / 'tools'):
        expected.update(p.relative_to(root).as_posix() for p in folder.glob('*.py'))
    legacy = set(OBSOLETE_TRACKED_FILES)
    for pattern in ('*.md',):
        expected.update(p.relative_to(root).as_posix() for p in (root / 'docs').glob(pattern)
                        if p.relative_to(root).as_posix() not in legacy)
    expected.update(p.relative_to(root).as_posix() for p in (root / '.github').rglob('*.yml'))
    expected.update(p.relative_to(root).as_posix() for p in (root / '.github').rglob('*.md'))
    unexpected = expected - sources
    if unexpected:
        issues.append('Unregistered code/docs: ' + ', '.join(sorted(unexpected)))
    return issues


def main() -> int:
    issues = audit_repository()
    if issues:
        for issue in issues:
            print('FAIL:', issue)
        return 1
    print(f'PASS: {len(SOURCE_FILES)} curated source files; {len(APP_FILES)} update files; no generated assets selected.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
