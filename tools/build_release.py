"""Create three intentional release ZIPs and a matching SHA256SUMS.txt.

- windows portable: from a successful Windows PyInstaller build only
- source: Python install, docs and maintainer sources
- update: current source-based installs only, with per-file integrity manifest

No duplicate 'GitHub-Repository', docs or brand-kit ZIPs inside Releases.
GitHub already offers a source archive; the source ZIP is the runnable bundle.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys
from zipfile import ZipFile, ZIP_DEFLATED, ZipInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from studio_core import APP_VERSION  # noqa: E402
from release_manifest import APP_FILES, SOURCE_FILES  # noqa: E402


def update_manifest() -> bytes:
    content = {
        'format': 'PinHarbor-update-sha256',
        'version': APP_VERSION,
        'files': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                  for name in APP_FILES},
    }
    return (json.dumps(content, indent=2, sort_keys=True, ensure_ascii=False) + '\n').encode('utf-8')


def _stable_write(z: ZipFile, source: Path, arcname: str) -> None:
    info = ZipInfo(arcname, date_time=(2020, 1, 1, 0, 0, 0))
    info.compress_type = ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    z.writestr(info, source.read_bytes(), compress_type=ZIP_DEFLATED, compresslevel=7)


def zip_files(target: Path, names: tuple[str, ...], prefix: str, *, integrity: bool = False) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(target, 'w', ZIP_DEFLATED, compresslevel=7) as z:
        for name in sorted(set(names)):
            path = ROOT / name
            if not path.is_file() or path.is_symlink():
                raise FileNotFoundError(f'Required release file missing or unsafe: {path}')
            _stable_write(z, path, f'{prefix}/{name}' if prefix else name)
        if integrity:
            info = ZipInfo(f'{prefix}/update-manifest.json', date_time=(2020, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            z.writestr(info, update_manifest())


def zip_windows(target: Path, dist_folder: Path) -> None:
    if not dist_folder.is_dir() or not (dist_folder / 'PinHarbor.exe').is_file():
        raise FileNotFoundError('Windows EXE output missing; run the Windows build first.')
    with ZipFile(target, 'w', ZIP_DEFLATED, compresslevel=7) as z:
        for path in sorted(dist_folder.rglob('*')):
            if path.is_file():
                _stable_write(z, path, (Path('PinHarbor') / path.relative_to(dist_folder)).as_posix())
        for name in ('LICENSE', 'NOTICE.md', 'THIRD-PARTY.md'):
            _stable_write(z, ROOT / name, f'PinHarbor/{name}')
        info = ZipInfo('README-START.txt', date_time=(2020, 1, 1, 0, 0, 0))
        info.compress_type = ZIP_DEFLATED
        z.writestr(info, 'PinHarbor for Windows. Extract all files, then start PinHarbor/PinHarbor.exe.\n'
                   'Keep the _internal folder next to the EXE. No standalone Python needed.\n')


def main() -> None:
    parser = argparse.ArgumentParser(description='Build public PinHarbor packages')
    parser.add_argument('--windows-dist', type=Path)
    parser.add_argument('--out', type=Path, default=ROOT / 'release')
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    # Idempotence: remove only known old generated release files.
    for old in out.glob('PinHarbor-v*.zip'):
        old.unlink()
    (out / 'SHA256SUMS.txt').unlink(missing_ok=True)
    packages = []
    for kind, names in [('source', SOURCE_FILES), ('update', APP_FILES)]:
        filename = out / f'PinHarbor-v{APP_VERSION}-{kind}.zip'
        zip_files(filename, names, f'PinHarbor-v{APP_VERSION}', integrity=(kind == 'update'))
        packages.append(filename)
    if args.windows_dist:
        filename = out / f'PinHarbor-v{APP_VERSION}-Windows-portable.zip'
        zip_windows(filename, args.windows_dist)
        packages.insert(0, filename)
    sums = '\n'.join(f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}' for p in packages) + '\n'
    (out / 'SHA256SUMS.txt').write_text(sums, encoding='utf-8')
    for p in packages:
        print(f'Created {p.name} ({p.stat().st_size:,} bytes)')
    print(f'Checksums: {out / "SHA256SUMS.txt"}')


if __name__ == '__main__':
    main()
