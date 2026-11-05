# Maintaining and releasing PinHarbor

This guide is for repository maintainers, not ordinary users.

## Update an existing v2.5 repository

1. Back up your current Git working tree. Keep your private downloads separate.
2. Extract the new **GitHub Repository ZIP**, then copy its contents **into the existing repository folder**. Preserve the existing `.git` directory; do not start from a new, unrelated folder.
3. Run `Publish to GitHub.bat` in that existing folder. It checks your GitHub CLI authentication and requires the explicit `PUBLISH` confirmation.
4. The tool stages only allowlisted source files and untracks known v2.5.0 duplicates using `git rm --cached` (local copies are retained). It refuses to commit unrelated pre-staged files. No arbitrary files are removed.
5. Confirm the changes landed on `main`, then review GitHub Actions.

Local preflight:

```powershell
python tools/github_publish.py --repo pinharbor
python tools/verify_repository.py
python -m unittest discover -s tests -v
```

## Builds and releases

Every push to `main` runs tests and attempts a Windows build. When it passes, download the Windows ZIP from **Actions → Artifacts**, then test the GUI, images, video and cancellation on real Windows hardware.

After manual QA, tag the commit:

```powershell
git tag -a v2.6.0 -m "PinHarbor 2.6.0 beta"
git push origin v2.6.0
```

The tag must match `APP_VERSION`. CI creates a **draft prerelease**, which must be manually reviewed and published. End users should download assets from Releases; do **not** commit generated ZIPs to Git.

The release assets are limited to Windows portable, source, update and SHA256 checksums. Third-party binaries may carry different license obligations; review `NOTICE.md` and `THIRD-PARTY.md` before public redistribution.
