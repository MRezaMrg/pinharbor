"""Offline preflight ensuring source packages contain no accidental app state."""
from __future__ import annotations
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from release_manifest import APP_FILES, SOURCE_FILES  # noqa: E402


def audit_repository(root: pathlib.Path = ROOT) -> list[str]:
    issues: list[str] = []
    files = set(SOURCE_FILES)
    if len(files) != len(SOURCE_FILES):
        issues.append("Duplicate paths in SOURCE_FILES")
    if not set(APP_FILES) <= files:
        issues.append("Update files not included in source distribution")
    for name in files:
        p = pathlib.PurePosixPath(name)
        if p.is_absolute() or any(part in {".", ".."} for part in p.parts):
            issues.append(f"Unsafe path: {name}")
            continue
        f = root / name
        if not f.is_file() or f.is_symlink():
            issues.append(f"Missing/not regular: {name}")
    expected = set()
    for folder in (root, root / "tests", root / "tools"):
        expected.update(f.relative_to(root).as_posix() for f in folder.glob("*.py"))
    expected.update(f.relative_to(root).as_posix() for f in (root / "docs").glob("*.md"))
    expected.update(f.relative_to(root).as_posix() for f in (root / ".github").rglob("*.yml"))
    expected.update(f.relative_to(root).as_posix() for f in (root / ".github").rglob("*.md"))
    missing = expected - files
    if missing:
        issues.append("Not registered for GitHub ZIP: " + ", ".join(sorted(missing)))
    for name in files:
        banned = (".pinterest-studio", ".env", "/.git/", "__pycache__", "cookies.txt", "download_archive.sqlite3")
        if any(x in name for x in banned):
            issues.append(f"Private/build file selected: {name}")
    return issues


def main() -> int:
    findings = audit_repository()
    if findings:
        for issue in findings:
            print("FAIL:", issue)
        return 1
    print(f"PASS: {len(SOURCE_FILES)} files in curated GitHub source ZIP; no unregistered source or docs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
