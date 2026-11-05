# PinHarbor notices and redistribution

The original PinHarbor application code and project artwork are provided under the repository's MIT license. **This does not change or sublicense third-party dependencies.**

Important dependencies include:

- **gallery-dl:** GPL-2.0-only ([upstream](https://github.com/mikf/gallery-dl)). PinHarbor invokes its extractor, and PyInstaller's self-contained build bundles it. Distribution of such a combined binary may carry GPL obligations. A maintainer must review the complete source-code/distribution requirements before publicly offering the compiled ZIP.
- **PySide6 / Qt:** open-source or commercial licensing, including LGPLv3/GPL options ([Qt for Python](https://pypi.org/project/PySide6/)). Respect third-party license notices and the applicable end-user rights when redistributing Qt libraries.
- **imageio-ffmpeg / FFmpeg:** the wrapper's BSD-2-Clause license is distinct from the embedded FFmpeg executable's build-specific licensing. Examine the exact FFmpeg binary and its configuration before redistributing it.
- **yt-dlp, PySocks and other transitive modules:** each has its own license. See [`THIRD-PARTY.md`](THIRD-PARTY.md) and the licenses bundled with each distribution.

The Windows build collects available installed distribution license files into a `licenses/` folder. These gathered files are a **starting point only**; missing notices and upstream obligations require verification before publishing a stable binary.

This notice is not legal advice. PinHarbor is not affiliated with Pinterest. Users must respect rights and permissions for media they download.
