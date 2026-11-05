# PinHarbor 2.5.0 — Reliability & GitHub-ready workflow

PinHarbor 2.5 improves installation/update safety, the board library, and the public publishing workflow. It preserves v2.x queue/settings/archive compatibility.

**Highlights**
- Update ZIPs include SHA-256 per-file integrity records; existing media/archives are excluded from application-file replacement.
- Changed Python dependency requirements trigger a repair/installation on the next source launch.
- The app shows live board-link validation, a quick start guide, and an offline download-readiness check.
- Internal app artwork no longer contaminates the gallery when saving beside the application.
- A curated, opt-in GitHub CLI publication assistant, 2-language guide, and repository audit.
- Improved CI: Python 3.10/3.12 on Windows/Linux, Qt offscreen smoke test and portable Windows packaging.
- Release ZIPs include project notices; package metadata legal notices are collected for review.

**Installation:** End users should download the *Windows-portable* ZIP produced by GitHub Actions. Source and Update ZIPs are offered separately. Update ZIP applies to older **source installations**, not EXE bundles.

**Review before publication:** The Windows GUI, clean-machine EXE, live image/video board downloads and distribution license compliance remain to be verified by the release maintainer. GitHub releases are generated as **drafts**.
