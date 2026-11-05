"""Produce curated, reproducible source/docs/brand/update and optional Windows ZIPs.

Usage:
  python tools/build_release.py
  python tools/build_release.py --windows-dist dist/PinHarbor

No user media, cookies, settings, or internal state are packed.
"""
from __future__ import annotations
import argparse
import hashlib
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED, ZipInfo
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from studio_core import APP_VERSION  # noqa: E402
from release_manifest import APP_FILES, SOURCE_FILES  # noqa: E402


def update_manifest() -> bytes:
    import json
    manifest = {
        "format": "PinHarbor-update-sha256",
        "version": APP_VERSION,
        "files": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in APP_FILES},
    }
    return (json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")



def _stable_write(z: ZipFile, path: Path, archive_name: str) -> None:
    """Use fixed timestamp/permissions to avoid time-dependent source ZIP hashes."""
    info = ZipInfo(archive_name, date_time=(2020, 1, 1, 0, 0, 0))
    info.compress_type = ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    z.writestr(info, path.read_bytes(), compress_type=ZIP_DEFLATED, compresslevel=7)


def zip_files(target: Path, names: tuple[str, ...], prefix: str, *, integrity: bool = False) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(target, 'w', ZIP_DEFLATED, compresslevel=7) as z:
        for filename in sorted(set(names)):
            p = ROOT / filename
            if not p.is_file() or p.is_symlink():
                raise FileNotFoundError(f'Required release file missing/unsafe: {p}')
            name = f'{prefix}/{filename}' if prefix else filename
            _stable_write(z, p, name)
        if integrity:
            z.writestr(f"{prefix}/update-manifest.json", update_manifest())


DOC_FILES = tuple(f for f in SOURCE_FILES if f.startswith('docs/') or
                  ('/' not in f and (f.endswith('.md') or f in ('START-HERE.txt', 'LICENSE'))))
BRAND_FILES = tuple(f for f in SOURCE_FILES if f.startswith('assets/')) + ('docs/BRAND-GUIDE.md',)


def zip_windows(target: Path, dist_folder: Path) -> None:
    if not dist_folder.is_dir() or not (dist_folder / 'PinHarbor.exe').is_file():
        raise FileNotFoundError('Windows EXE output is missing; build with PyInstaller on Windows first.')
    with ZipFile(target, 'w', ZIP_DEFLATED, compresslevel=7) as z:
        for f in sorted(dist_folder.rglob('*')):
            if f.is_file():
                _stable_write(z, f, (Path('PinHarbor') / f.relative_to(dist_folder)).as_posix())
        for notice in ('LICENSE', 'NOTICE.md', 'THIRD-PARTY.md'):
            _stable_write(z, ROOT / notice, f'PinHarbor/{notice}')
        z.writestr('README-START.txt',
                   'PinHarbor portable Windows release.\nExtract ALL files and run PinHarbor\\PinHarbor.exe.\n'
                   'Keep the _internal folder beside the EXE. No Python installation required.\n'
                   'For support visit the GitHub repository.\n')


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--windows-dist', type=Path)
    parser.add_argument('--out', type=Path, default=ROOT / 'release')
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    packages = []
    for label, files in [('source', SOURCE_FILES), ('UPDATE', APP_FILES),
                         ('GitHub-Repository', SOURCE_FILES), ('Docs-FA-EN', DOC_FILES), ('Brand-Kit', BRAND_FILES)]:
        path = out / f'PinHarbor-v{APP_VERSION}-{label}.zip'
        prefix = f'PinHarbor-v{APP_VERSION}' if label in {'source', 'UPDATE'} else ''
        zip_files(path, files, prefix, integrity=(label == 'UPDATE'))
        packages.append(path)
    if args.windows_dist:
        portable = out / f'PinHarbor-v{APP_VERSION}-Windows-portable.zip'
        zip_windows(portable, args.windows_dist)
        packages.append(portable)
    checksums = []
    for archive in packages:
        checksums.append(f'{hashlib.sha256(archive.read_bytes()).hexdigest()}  {archive.name}')
    (out / 'SHA256SUMS.txt').write_text('\n'.join(checksums)+'\n',encoding='utf-8')
    for path in packages: print(f'Created {path} ({path.stat().st_size:,} bytes)')
    print('SHA256SUMS:',out / 'SHA256SUMS.txt')


if __name__ == '__main__':
    main()
