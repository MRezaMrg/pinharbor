# PinHarbor troubleshooting

## My board shows 45 pins, but only 25 files downloaded

First, distinguish **pins discovered** from **files downloaded**. A pin can include more than one media file or none that are retrievable. In v2.6, the queue shows unique pin IDs observed by the download engine, plus new and skipped file counts.

1. Enter **45** in **Expected board pins** for that single board (only a reference; Pinterest's count can change).
2. In **Pinterest login**, select the browser where you are already signed in to Pinterest (Chrome, Edge, or Firefox). If cookies are locked, fully close the browser and retry.
3. Retry the same board. Previously downloaded files are skipped via the archive.
4. If a download cap was enabled in the past, remove it using the visible **Remove download limit** button.
5. Expand technical details only if the count remains short. Look for authentication, 429 rate-limiting, or unavailable-content errors.

**Neither the reported Pinterest pin count nor the observed count guarantees complete access.** This app cannot force Pinterest to expose missing pins.

## Videos are missing

Some videos need yt-dlp and FFmpeg. For source installs, run `Update Engines.bat`. Certain video types may remain inaccessible.

## Cannot start the app

Use `Run on Windows.bat` with Python 3.10+ for a source installation. For a Windows portable release, extract the *entire* ZIP and keep `_internal` beside the EXE.

## Language didn't change

Choose Settings → Language, then fully close and restart PinHarbor.

## Report a problem

Open a [GitHub issue](https://github.com/MRezaMrg/pinharbor/issues). Include the app version, install type and observed pin/file counts. Never paste cookies, tokens, proxy passwords, or private URLs.
