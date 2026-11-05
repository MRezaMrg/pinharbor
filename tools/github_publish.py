"""Interactive, opt-in GitHub publisher using official Git and GitHub CLI.

Safe default is DRY RUN. On execute: stage only curated project files (never
user media), commit, and create/push a repository. Never creates a release/tag.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from release_manifest import SOURCE_FILES  # noqa: E402

REPO_RE = re.compile(r"^(?:[A-Za-z0-9][A-Za-z0-9-]{0,38}/)?[A-Za-z0-9._-]{1,100}$")


def repo_name(value: str) -> str:
    value = value.strip()
    if not REPO_RE.fullmatch(value) or ".." in value or value.endswith(".git"):
        raise ValueError("Invalid repository slug. Use 'pinharbor' or 'OWNER/pinharbor'.")
    return value


def selected_uploads() -> tuple[str, ...]:
    missing = [f for f in SOURCE_FILES if not (ROOT / f).is_file()]
    if missing:
        raise ValueError("Missing project files: " + ", ".join(missing))
    return tuple(sorted(SOURCE_FILES))


def execute(args: list[str], *, capture: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=ROOT, check=True, text=True,
                          stdout=subprocess.PIPE if capture else None,
                          stderr=subprocess.PIPE if capture else None)


def has_git() -> bool:
    return (ROOT / ".git").exists()


def existing_origin() -> str:
    result = subprocess.run(["git", "remote", "get-url", "origin"], cwd=ROOT,
                            capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else ""


def origin_matches_repo(remote: str, slug: str) -> bool:
    if not remote:
        return False
    # Compare repository basename; if the owner was supplied, enforce it too.
    norm = remote.rstrip("/").removesuffix(".git")
    if "github.com" not in norm.lower():
        return False
    parts = norm.replace(":", "/").split("/")
    suffix = slug.lower().split("/")
    return [x.lower() for x in parts[-len(suffix):]] == suffix


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Publish curated PinHarbor sources to GitHub")
    p.add_argument("--repo", default="pinharbor", help="Repository name or OWNER/name")
    p.add_argument("--visibility", choices=("public", "private"), default="public")
    p.add_argument("--execute", action="store_true", help="Opt in to actual git/gh commands")
    p.add_argument("--yes", action="store_true", help="Explicit approval for scripted execution")
    args = p.parse_args(argv)
    try:
        repo = repo_name(args.repo)
        selected = selected_uploads()
        print(f"Repository: {repo} ({args.visibility})")
        print(f"Curated source files: {len(selected)}")
        print("No media, user archives, cookies, proxy or local secrets are selected.")
        print("Release: NOT created. Tags must be pushed separately after QA.")
        if not args.execute:
            print("DRY RUN. To continue, run with --execute (requires Git and GitHub CLI).")
            return 0
        for tool in ("git", "gh"):
            if not shutil.which(tool):
                raise RuntimeError(f"{tool} is not installed or available in PATH.")
        execute(["gh", "auth", "status"])
        if not args.yes:
            answer = input("Type PUBLISH to upload selected source files to GitHub: ").strip()
            if answer != "PUBLISH":
                print("Cancelled. No files uploaded.")
                return 2
        if not has_git():
            execute(["git", "init"])
        execute(["git", "branch", "-M", "main"])
        execute(["git", "add", "--", *selected])
        staged = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT)
        if staged.returncode == 1:
            execute(["git", "commit", "-m", "Publish PinHarbor sources and documentation"])
        elif staged.returncode != 0:
            raise RuntimeError("Could not inspect staged changes.")
        origin = existing_origin()
        if origin:
            if not origin_matches_repo(origin, repo):
                raise RuntimeError("Existing origin does not match requested repository. Nothing was pushed.")
            execute(["git", "push", "-u", "origin", "main"])
        else:
            execute(["gh", "repo", "create", repo,
                     "--public" if args.visibility == "public" else "--private",
                     "--source", str(ROOT), "--remote", "origin", "--push"])
        print("GitHub source upload completed. Check Actions before tagging a release.")
        return 0
    except (ValueError, RuntimeError, subprocess.CalledProcessError, OSError) as exc:
        print(f"Publish stopped: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
