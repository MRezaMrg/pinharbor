"""Safe, explicit initial publish *or* sync of a curated PinHarbor repo.

Dry run by default. --execute + typed PUBLISH confirmation are required.
Only allowlisted source files are committed. Known v2.5.0 duplicates are
untracked with git rm --cached (local files preserved); unknown tracked files
are never automatically deleted. No tags, Releases or force push.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import re
import shutil
import subprocess
import sys
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from release_manifest import SOURCE_FILES, OBSOLETE_TRACKED_FILES  # noqa: E402

REPO_RE = re.compile(r'^(?:[A-Za-z0-9][A-Za-z0-9-]{0,38}/)?[A-Za-z0-9._-]{1,100}$')


def repo_name(value: str) -> str:
    value = value.strip()
    if not REPO_RE.fullmatch(value) or '..' in value or value.endswith('.git'):
        raise ValueError("Invalid repository slug; use 'pinharbor' or 'OWNER/pinharbor'.")
    return value


def selected_uploads() -> tuple[str, ...]:
    missing = [f for f in SOURCE_FILES if not (ROOT / f).is_file() or (ROOT / f).is_symlink()]
    if missing:
        raise ValueError('Missing/unsafe source files: ' + ', '.join(missing))
    return tuple(sorted(SOURCE_FILES))


def execute(args: list[str], *, capture: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=ROOT, check=True, text=True,
                          stdout=subprocess.PIPE if capture else None,
                          stderr=subprocess.PIPE if capture else None)


def git_list(args: list[str]) -> set[str]:
    result = subprocess.run(['git', *args, '-z'], cwd=ROOT, check=True, capture_output=True)
    return {v.decode('utf-8', 'surrogateescape') for v in result.stdout.split(b'\0') if v}


def has_git() -> bool:
    return (ROOT / '.git').exists()


def existing_origin() -> str:
    result = subprocess.run(['git', 'remote', 'get-url', 'origin'], cwd=ROOT, capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else ''


def origin_matches_repo(remote: str, slug: str) -> bool:
    """Require the *actual* GitHub host, not a substring in an attacker domain."""
    if not remote:
        return False
    remote = remote.strip()
    if remote.startswith('git@github.com:'):
        path = remote[len('git@github.com:'):]
    else:
        parsed = urlsplit(remote)
        if parsed.hostname != 'github.com' or parsed.scheme not in {'https', 'ssh', 'git'}:
            return False
        path = parsed.path.lstrip('/')
    components = path.removesuffix('.git').rstrip('/').split('/')
    if len(components) != 2 or any(not c for c in components):
        return False
    expected = slug.casefold().split('/')
    actual = [c.casefold() for c in components]
    return actual[-len(expected):] == expected


def obsolete_tracked_paths(paths: set[str]) -> tuple[str, ...]:
    """Explicitly remove tracked v2.5.0 junk only; no unrestricted globs."""
    obsolete = set(OBSOLETE_TRACKED_FILES)
    for name in paths:
        if name.startswith('release/') and (name.endswith('.zip') and Path(name).name.startswith('PinHarbor-v2.')
                                            or name == 'release/SHA256SUMS.txt'):
            obsolete.add(name)
        if '__pycache__' in name.split('/') and name.endswith(('.pyc', '.pyo')):
            obsolete.add(name)
    return tuple(sorted(paths & obsolete))


def ensure_staging_safe(allowed: set[str]) -> None:
    staged = git_list(['diff', '--cached', '--name-only'])
    other = staged - allowed
    if other:
        raise RuntimeError('Unrelated files already staged. Unstage them before publishing: '
                           + ', '.join(sorted(other)))


def sync_repository(repo: str, selected: tuple[str, ...], visibility: str = "public") -> None:
    """Update index safely; commit *only* curated changes and known removals."""
    newly_initialized = not has_git()
    if newly_initialized:
        execute(['git', 'init', '-b', 'main'])
    else:
        current = execute(['git', 'branch', '--show-current'], capture=True).stdout.strip()
        if current != 'main':
            raise RuntimeError(f"Current branch '{current}' is not main. Switch to main first.")
    origin = existing_origin()
    if origin and not origin_matches_repo(origin, repo):
        raise RuntimeError('Existing Git remote does not match the requested repository. No push performed.')
    tracked = git_list(['ls-files', '--cached'])
    obsolete = obsolete_tracked_paths(tracked)
    unrelated_tracked = tracked - set(selected) - set(obsolete)
    if unrelated_tracked:
        raise RuntimeError('Unknown files are already Git-tracked; inspect them manually before publishing: '
                           + ', '.join(sorted(unrelated_tracked)))
    allowed = set(selected) | set(obsolete)
    ensure_staging_safe(allowed)
    execute(['git', 'add', '--', *selected])
    if obsolete:
        # --cached removes from the Git index, *not* from the user's disk.
        execute(['git', 'rm', '--cached', '-q', '--ignore-unmatch', '--', *obsolete])
    ensure_staging_safe(allowed)
    staged = git_list(['diff', '--cached', '--name-only'])
    print(f'Changed files staged: {len(staged)}; retired Git-tracked paths: {len(obsolete)}')
    if obsolete:
        print('Retired files remain on disk (only removed from Git):')
        for item in obsolete:
            print('  -', item)
    # No git commit if there are no changes.
    if staged:
        execute(['git', 'commit', '-m', 'chore: simplify repository and refresh PinHarbor sources'])
    if origin:
        execute(['git', 'push', '-u', 'origin', 'main'])
    else:
        execute(['gh', 'repo', 'create', repo, '--public' if visibility == 'public' else '--private',
                 '--source', str(ROOT), '--remote', 'origin', '--push'])



def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description='Publish curated PinHarbor files to GitHub')
    p.add_argument('--repo', default='pinharbor', help='Name or OWNER/name')
    p.add_argument('--visibility', choices=('public', 'private'), default='public')
    p.add_argument('--execute', action='store_true', help='Opt in to actual Git/GitHub upload')
    args = p.parse_args(argv)
    try:
        repo = repo_name(args.repo)
        selected = selected_uploads()
        print(f'Repository: {repo} ({args.visibility})')
        print(f'Included source files: {len(selected)}; ignored: downloads, cookies, build and release ZIPs.')
        if not args.execute:
            print('DRY RUN: nothing committed or uploaded. Run with --execute to confirm publishing.')
            return 0
        for tool in ('git', 'gh'):
            if not shutil.which(tool):
                raise RuntimeError(f'{tool} not found in PATH. Install it and reopen PowerShell.')
        # Do all safe prechecks before asking for confirmation and before commits.
        execute(['gh', 'auth', 'status'])
        if has_git():
            origin = existing_origin()
            if origin and not origin_matches_repo(origin, repo):
                raise RuntimeError('Existing origin points to another repository; refusing to modify it.')
            pre_staged = git_list(['diff', '--cached', '--name-only'])
            tracked = git_list(['ls-files', '--cached'])
            removable = set(obsolete_tracked_paths(tracked))
            whitelist = set(selected) | removable
            if tracked - whitelist:
                raise RuntimeError('Unrecognized tracked Git files exist. Review these before publishing: '
                                   + ', '.join(sorted(tracked - whitelist)))
            if pre_staged - whitelist:
                raise RuntimeError('Unrelated staged files exist; unstage them before proceeding.')
        print('Only listed project files will be committed. Known old docs will be untracked, never deleted.')
        if input('Type PUBLISH to upload to GitHub: ').strip() != 'PUBLISH':
            print('Cancelled: no repository files changed.')
            return 2
        sync_repository(repo, selected, args.visibility)
        print('Done. Review GitHub Actions before creating a release tag.')
        return 0
    except (ValueError, RuntimeError, OSError, subprocess.CalledProcessError) as exc:
        print(f'Publish stopped: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
