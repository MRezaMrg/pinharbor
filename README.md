<div align="center">
  <img src="assets/pinharbor-banner.png" alt="PinHarbor artwork" width="100%" />

  # PinHarbor
  **Save Pinterest board images and videos. Organize them locally.**

  **English** · [فارسی](README-FA.md) · [Download](https://github.com/MRezaMrg/pinharbor/releases) · [Report an issue](https://github.com/MRezaMrg/pinharbor/issues)
</div>

PinHarbor is a free, independent Windows desktop application with a simple English/Persian interface, a download queue, and a built-in media library. Its dark burgundy-and-rose design keeps the focus on your boards and files.

> **Beta:** PinHarbor is under active development. Pinterest may not expose every pin to third-party tools, even on a public board. PinHarbor is not affiliated with, endorsed by, or operated by Pinterest.

## What can it do?

- Save accessible images and videos from Pinterest boards and board sections.
- Download several boards, pause by stopping and retry later, and skip duplicates on subsequent runs.
- Browse, search and filter saved images/videos in the local library.
- Use your logged-in Chrome, Edge or Firefox session when a public download finds fewer pins.
- **Check possible missing pins:** see the number of unique pins detected; optionally enter the pin count displayed on Pinterest to flag an incomplete result.
- Switch between **English and Persian** in Settings (restart required).
- Choose a download folder. Keep your downloaded files and archive when upgrading a source installation.

**Important:** The number of pins is not the number of files: one pin can contain several files, while others may be inaccessible. The observed pin count cannot guarantee complete coverage of a board.

## Download and install

Get a package from [GitHub Releases](https://github.com/MRezaMrg/pinharbor/releases):

| Package | Who is it for? | How to launch |
|---|---|---|
| **Windows portable ZIP** | Most Windows users, once a tested build is available | Extract the whole ZIP and open `PinHarbor.exe` in the `PinHarbor` folder. |
| **Source ZIP** | Users with Python 3.10+ | Extract and double-click `Run on Windows.bat` (first run downloads dependencies). |
| **Update ZIP** | Existing **source installation** only | Close the app, extract the ZIP elsewhere, run `Upgrade Existing Installation.bat` and choose your old app folder. |

An update ZIP **does not update a compiled EXE**. All downloaded media remains in its existing output directory. See [Install and update help](docs/INSTALL-EN.md).

## Quick start

1. Paste a Pinterest board link, such as `https://www.pinterest.com/username/board-name/`.
2. Choose **Download now**. You can add multiple URLs, one per line.
3. Open **Library** to view saved media. You can change the destination folder before starting.
4. If fewer pins are found than expected, enter the displayed count in **Expected board pins**, select a browser where you're logged into Pinterest, and try the same board again. Previously downloaded files are skipped.

To switch language: **Settings → Language → English / فارسی → restart the app**.

## Having trouble?

See [Troubleshooting](docs/TROUBLESHOOTING-EN.md) / [راهنمای رفع مشکلات](docs/TROUBLESHOOTING-FA.md). When reporting bugs, state your PinHarbor version, whether you were signed in, and the **observed** pin/file counts. Never share cookies, proxy credentials or private URLs.

## Privacy and rights

Your downloaded media, queue and archive are local to your computer. When selected, the download engine reads an existing browser session locally; the app does not ask for your Pinterest password. It sends requests to Pinterest/media hosts when downloading. See the [privacy explanation](docs/PRIVACY-EN.md).

Download and reuse only material you have the right to access and use, respecting intellectual-property rights and applicable platform terms.

PinHarbor source is distributed under the [MIT License](LICENSE). Bundled dependencies may have their own license obligations; see [Third-party components](THIRD-PARTY.md) and [Notices](NOTICE.md).

<details><summary>For contributors and maintainers</summary>

See [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md), and [maintainer documentation](docs/MAINTAINER-EN.md). The source package can be tested with `python -m unittest discover -s tests -v`.

</details>

*Artwork above is a brand illustration, not a screenshot of the running app.*
