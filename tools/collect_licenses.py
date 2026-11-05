"""Gather legal notices included in installed Python distribution metadata.

Best-effort: this does not replace a maintainer legal review of Qt or FFmpeg.
"""
from __future__ import annotations
import importlib.metadata as metadata
from pathlib import Path
import shutil
import sys

PACKAGES = ('PySide6', 'PySide6_Essentials', 'PySide6_Addons', 'shiboken6',
            'gallery-dl', 'yt-dlp', 'imageio-ffmpeg', 'PySocks', 'PyInstaller')


def collect(destination: Path) -> list[str]:
    destination.mkdir(parents=True, exist_ok=True)
    missing: list[str] = []
    summary = []
    for name in PACKAGES:
        try:
            dist = metadata.distribution(name)
        except metadata.PackageNotFoundError:
            missing.append(name + ' (not installed)')
            continue
        candidates = []
        for f in dist.files or ():
            if f.name.lower().startswith(('license', 'copying', 'notice')) or 'licenses' in [p.lower() for p in f.parts]:
                path = Path(dist.locate_file(f))
                if path.is_file() and path.stat().st_size < 2_000_000:
                    candidates.append(path)
        dest = destination / name
        dest.mkdir(exist_ok=True)
        count = 0
        for file in candidates:
            # Flatten safely while preserving uniquely named notice paths.
            target = dest / f'{count + 1:02d}-{file.name}'
            shutil.copyfile(file, target)
            count += 1
        summary.append(f'{name} {dist.version}: {count} license/notice files copied')
        if not count:
            missing.append(name + ' (no metadata license file found)')
    (destination / 'PACKAGE-LICENSES.txt').write_text(
        '\n'.join(summary + ['', 'Maintainer review required:', *(missing or ['none flagged'])]) + '\n',
        encoding='utf-8')
    return missing


def main() -> int:
    if len(sys.argv) != 2:
        print('Usage: python tools/collect_licenses.py DESTINATION')
        return 2
    flagged = collect(Path(sys.argv[1]))
    for item in flagged:
        print('LICENSE REVIEW:', item)
    # Notes may be absent from wheels; manual release review remains a gate.
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
