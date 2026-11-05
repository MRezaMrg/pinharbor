# Installation & update guide (English)

## 1. Choose a package

- **Windows portable ZIP:** built by GitHub Actions from a release tag. Extract the entire `PinHarbor` directory; run `PinHarbor.exe`. Do not separate the executable from its `_internal` folder. You do **not** need a separate Python installation. The ZIP is available only after the owner successfully runs the Windows build and publishes a Release.
- **Source ZIP:** extract to a writable folder and double-click `Run on Windows.bat`. Requires Python 3.10+ and an internet connection on first run to install PySide6, gallery-dl, yt-dlp and optional FFmpeg support.
- **Update ZIP:** for existing source-based v2.1–2.3 installations only. It cannot replace an installed compiled EXE.

## 2. Download your first board

1. Launch the program. The UI is currently Persian.
2. Paste a board URL, for example `https://www.pinterest.com/username/board-name/`, into the address field. You can enter several URLs, one per line.
3. Click «دانلود از لینک‌ها» (Download entered links). Alternatively, add URLs to the saved queue using «فقط افزودن به صف» (Add to queue only).
4. Select your destination under Settings if you do not want files beside the app. Make sure the location is writable.
5. Monitor the queue tab, then open the Media Library tab («کتابخانه رسانه‌ها»).

For private/account-restricted content, selecting a browser in advanced settings uses that browser's local cookies (not your password). Do not send cookie files to anybody.

## 3. Updating from an older source installation

1. Close all PinHarbor / Pinterest Board Studio windows.
2. Extract the **Update ZIP somewhere else**. Never extract it over your current application folder by hand.
3. Run `Upgrade Existing Installation.bat`; choose the folder containing the *old* `Run on Windows.bat` and `studio_core.py`.
4. Read the success message, then start the upgraded software from the **old folder**.
5. Existing download files, `.pinterest-studio/download_archive.sqlite3` and Qt settings are preserved. The legacy Qt settings organization/application ID is intentionally kept to support migration.
6. To roll back, close the program and run `Rollback Last Update.bat` in that updated folder. A snapshot of replaced app files is stored under `.pinterest-studio/app-backups/`.

**Important:** When upgrading from a very old version which did not remember a custom output directory, select it again on first launch. The updater does not manage standalone EXE installs. If the updater cannot locate Python, install Python or first launch the old source install.

## 4. Build a portable EXE on Windows

1. From source, run `Run on Windows.bat` once (creates its Python virtual environment).
2. Run `Build EXE (Windows).bat`.
3. Keep the entire `dist/PinHarbor/` directory together, including `PinHarbor.exe` and `_internal/`.
4. For distribution, ZIP the *whole directory*, not just the `.exe`.

GitHub Actions can generate the EXE ZIP automatically on a Windows runner when a release tag is pushed. The build does not imply the application is signed or has passed real-world downloader testing; test on Windows before promoting it to a stable release.

## 5. Known limitations

- Board-level total Pin counts are not always known; progress indicates completed/processed boards.
- Request rate limits, login restrictions and unavailable media can produce partial results.
- FFmpeg may be required by yt-dlp for some videos; the bundled dependency attempts to provide it.
- Windows is the advertised end-user platform; Python may run elsewhere, but other desktop platforms are not verified and no Mac/Linux installers are shipped.
- Downloaded files may be subject to third-party copyright and platform restrictions.
