# Changelog

## 2.5.0 — Reliability & Publish Workflow

- Added per-file SHA-256 validation for update ZIPs before changing the old installation.
- Improved Python source launcher to reinstall dependencies when requirements change.
- Added live board URL feedback, quick guide, offline preflight and internal-artwork exclusion in media gallery.
- Curated one-command GitHub publisher (dry run by default) and bilingual release path.
- CI now verifies packaging, runs offline tests across two Python versions and checks Qt startup on a Windows runner.
- Collected third-party license notices and added publication safety guidance.

## 2.4.0 — GitHub Launch Kit

- Public-facing name **PinHarbor** and redesigned rose/burgundy icon and banner.
- English and Persian documentation for installation, updates, troubleshooting, privacy and releases.
- Repository community files: bug and feature issue forms, pull request template, contributing guide, security policy, code of conduct and support.
- Windows CI build/release pipeline for portable EXE ZIP, source ZIP, update ZIP and checksum list.
- Kept legacy `QSettings("PinterestBoardStudio", "Desktop")` and installation migration paths for existing users.
- Reworked UI header branding to use the new icon rather than a plain P monogram.
- No new promises about Pinterest extractor coverage; downloader behavior is that of v2.3.

## 2.3.0 — Burgundy / Rose Glass

- Burgundy, pastel pink and near-black theme; translucent card treatment and Persian font selection.

## 2.2.0 — Upgrade and UX

- In-place source updater with backups and rollback; queue and gallery UX, performance and path persistence improvements.

## 2.1.0 — Reliability

- Process control, thumbnail threading, improved queue recovery and diagnostics.

## 2.0.0 — Queue and gallery

- Queue management, media library and advanced settings.
