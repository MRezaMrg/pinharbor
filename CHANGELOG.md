# Changelog

## 2.6.0 — Board coverage and bilingual interface

### Improved

- English and Persian interface; selection is saved and applied on the next launch.
- Shows distinct discovered Pinterest pin IDs alongside downloaded and skipped files.
- Optional user-entered expected pin count flags a possible incomplete single-board result without claiming that Pinterest's total is definitive.
- Incomplete boards appear as **Needs review** and can be retried with browser sign-in; previously downloaded files remain archived.
- Previously configured download caps are surfaced on the main download screen with a one-click reset.
- Advanced settings and engine diagnostics remain accessible but collapsed by default.
- Simplified bilingual public README and troubleshooting instructions; contributor guidance stays in maintainer documentation.
- New offline regression tests for pin counting, archive/session migration, English strings and command-line options, plus dual-language GUI smoke coverage on Windows CI.

### Compatibility

- Existing `.pinterest-studio` download archives, folders and legacy `QSettings` identity are preserved.
- Source installations can upgrade via the Update ZIP; Windows EXE packages require a separate portable release.

### Important limits

- A successful run cannot guarantee that Pinterest exposed every pin. The expected count is a comparison aid, not an authoritative API count.
- Direct testing of the supplied live board and actual Windows GUI/executable was not possible in the development environment; use CI and manual QA before Stable release.
