# Third-party components / وابستگی‌های ثالث

This repository ships **PinHarbor source code and original artwork**. Installation/build downloads and bundles external packages, each subject to its own license and terms:

- [PySide6 / Qt for Python](https://pypi.org/project/PySide6/) — Qt bindings; dual/multiple licensed; review LGPLv3/GPL/commercial terms for your distribution model.
- [gallery-dl](https://github.com/mikf/gallery-dl) — **GPL-2.0-only**; supported-site extractor and archive. Bundled EXE redistribution may trigger additional GPL compliance obligations.
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) — media download engine used for some video formats.
- [imageio-ffmpeg](https://github.com/imageio/imageio-ffmpeg) — optional FFmpeg binary provider; FFmpeg has its own license configuration and obligations.
- [PySocks](https://pypi.org/project/PySocks/) — optional SOCKS proxy support.
- [PyInstaller](https://pyinstaller.org/) — Windows packaging; build-time only.
- [Vazirmatn](https://github.com/rastikerdar/vazirmatn) — optional system font, **not bundled**.

Before publicly distributing a compiled EXE, audit the exact versions and included Qt, FFmpeg and PyInstaller notices/licenses produced by the build. The project's MIT license does not replace licenses of third-party components or media. Pinterest is a third-party trademark and service; PinHarbor is unaffiliated.

## Compiled distribution checklist

A Windows `PinHarbor.exe` package may combine LGPL/GPL-licensed parts with MIT-licensed application code. Before publishing the binary, inspect the collected `licenses/` folder, Qt libraries and the **exact FFmpeg build**. Ensure third-party notices, any required corresponding source and applicable users' rights are provided. See [NOTICE.md](NOTICE.md). These checks are a publication gate; do not equate a successful build with legal clearance.
