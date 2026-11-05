# Troubleshooting (English)

| Symptom | What to do |
|---|---|
| `Run on Windows.bat` closes or Python is missing | Install Python 3.10+, ensure it is accessible to `py` or `python`, launch the Batch file from an extracted writable folder. |
| First launch fails to install packages | Check network, firewall/proxy and disk space; run the Batch file again. Use a current Python version. |
| Invalid URL | Use the **board** or section URL with a board path (`pinterest.com/user/board/`), not a single pin or a search page. |
| No media returned / `403` | The board may require login or contain inaccessible media. If authorized, sign in to Pinterest in Chrome/Edge/Firefox and choose that browser in the app. |
| HTTP `429` | Rate limited; reduce pace, wait and retry later. Do not try to bypass access controls. |
| Missing or silent videos | Some video formats are unavailable, and yt-dlp/FFmpeg may need updating. Run `Update Engines.bat` for source installs. |
| Duplicate files skipped | Expected: SQLite download archive avoids re-downloading previously completed media. |
| Progress looks stuck | One board may have an unknown number of Pins. The bar counts boards, not total files. Review the technical log. |
| Destination folder error | Choose a different writable folder (e.g., in your home directory) and ensure sufficient disk space. |
| `.exe` missing files | Distribute the **entire** PyInstaller `dist/PinHarbor` folder, including `_internal`. |
| Weird Persian glyphs | Install the optional Vazirmatn font, restart the app, or choose a font available in Windows. |
| Upgrade failed | Close the old app, use a separately extracted Update ZIP and verify the selected folder is a source installation. If needed use the rollback script after a successful upgrade. |

When reporting a bug, include the version, OS, reproduction steps and a **redacted** log. Never attach a browser cookie database, your Pinterest password or proxy credentials. See [Support](../SUPPORT.md).
