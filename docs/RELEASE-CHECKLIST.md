# Maintainer release checklist / چک‌لیست انتشار

**Do not describe a build as tested on Windows solely because Python unit tests passed.**

- [ ] Confirm GitHub repository name/owner, project About description, license holder and logo rights.
- [ ] Verify the `PinHarbor-v2.5.0-UPDATE.zip` file hashes are checked before updating.
- [ ] Verify English/Persian docs and no placeholders, secrets, downloaded media or private URLs.
- [ ] Run `python tools/verify_repository.py` and `python -m unittest discover -s tests -v` locally and verify Windows CI jobs pass.
- [ ] Windows 10/11 GUI opens correctly (Persian/RTL fonts, new icon, all three tabs).
- [ ] Test a public board with image and video media **you have permission to download**.
- [ ] Test a section and multi-board queue; skipped duplicates, cancel and retry.
- [ ] Test custom destination, no-write permission error, browser login path and gallery previews.
- [ ] Test source upgrade from 2.3/2.4; confirm media/archive/queue remain; test rollback.
- [ ] Test Windows EXE on a clean Windows VM with **no Python installation**; keep `_internal` intact.
- [ ] Review third-party license obligations (especially gallery-dl GPL-2.0-only, Qt and the included FFmpeg build); determine code-signing/reputation plan.
- [ ] Create an annotated tag `v2.5.0`, push to GitHub, review action logs and Release assets before public announcement.
- [ ] Download the published ZIP on another machine; verify SHA256SUMS and unzip/launch.
- [ ] Add genuine app screenshots from a real installation (do **not** label the banner as a screenshot).
- [ ] Check private vulnerability reporting and optionally enable Discussions in GitHub settings.

**Commands**

```bash
python -m unittest discover -s tests -v
git tag -a v2.5.0 -m 'PinHarbor 2.5.0'
git push origin main
git push origin v2.5.0
```
