# Install and update PinHarbor

## Choose your download

For most Windows users, choose the **Windows portable ZIP** from [Releases](https://github.com/MRezaMrg/pinharbor/releases), once a tested build is published. Extract the complete ZIP and start `PinHarbor.exe` inside the `PinHarbor` folder. Keep `_internal` next to the EXE; you do not need Python.

For Python/source users, download the **Source ZIP**, extract it, and run `Run on Windows.bat`. Python 3.10+ and internet access are needed for the initial dependency installation.

## Start downloading

Paste a board URL in **Downloads**, choose **Download now**, then check the **Library** tab. You can enter multiple board URLs, one per line. Choose a destination folder before downloading if you do not want to save beside the app.

### Fewer pins than expected?

Enter Pinterest's displayed number in **Expected board pins** (one board at a time). If the result is flagged **Needs review**, select a browser where you're logged in to Pinterest, and retry. PinHarbor reuses its archive to skip already downloaded files. The displayed count is only an estimate: pins and media files are not equivalent.

## Update an existing source installation

1. Close PinHarbor completely.
2. Download and extract the **Update ZIP** in a *separate* folder.
3. Run `Upgrade Existing Installation.bat` from the extracted ZIP.
4. Choose the folder of your existing PinHarbor installation, containing `Run on Windows.bat` and `studio_core.py`.
5. Reopen the program from the **existing** folder.

Media, archive and settings are retained. If necessary, close the app and run `Rollback Last Update.bat` to restore previous application files.

**The Update ZIP does not update a compiled EXE.** Download a new Windows portable release instead.

To change language: **Settings → Language → English / فارسی**, then close and restart PinHarbor.

For technical contributors: see [Maintainer guide](MAINTAINER-EN.md).
