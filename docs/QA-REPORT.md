# QA status — 2026-11-05 · PinHarbor v2.5.0

Automated tests run locally in a non-Windows environment, with no live Pinterest connection. See the release checklist for tests that are **not** covered.

## Verified in this session

- Source and update ZIP generation using a curated file manifest.
- SHA-256 integrity verification and rejection of a modified update package before changing an existing installation.
- In-place upgrade and rollback contract against offline fixtures; previous release compatibility tests.
- Offline test suite: 73 passing tests, including migration from a real v2.4 source copy and rollback.
- GitHub publisher dry run, file allowlist and invalid-repository-name checks.
- Exclusion of app artwork from the local media gallery for the default application folder.
- Python syntax and ZIP integrity tests.

## Pending external validation

- Actual Windows PySide6 GUI operation and FFmpeg video preview (CI smoke test configured, not executed here).
- Real Pinterest board/section downloads, authentication, 429/retry paths.
- Running the self-contained EXE on clean Windows with no Python and preserving `_internal`.
- GitHub Actions workflow and draft GitHub Release, until pushed to a repository.
- Third-party redistribution license compliance, code signing and brand/trademark clearance.

**Release recommendation:** publish source documentation as a test/beta release if desired; do not mark binaries production-stable before the external checks pass.
