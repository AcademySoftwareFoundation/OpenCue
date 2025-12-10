#!/usr/bin/env python3
# ci/generate_helix_version.py

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Tuple


def get_version_in_path() -> Path:
    script_dir = Path(__file__).parent.resolve()
    toplevel_dir = script_dir.parent
    return toplevel_dir / "VERSION.in"


def run_command(cmd: List[str]) -> str:
    """Runs a command and returns its stripped stdout."""
    try:
        result = subprocess.run(
            cmd, check=True, capture_output=True, text=True, encoding="utf-8"
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(
            f"Command '{' '.join(cmd)}' failed with error:\n{e.stderr}",
            file=sys.stderr,
        )
        raise


def get_current_branch() -> str:
    """
    Return the current branch name, handling detached HEAD common in CI.

    Tries 'git branch --show-current' and falls back to parsing remote branches that contain HEAD.
    """
    try:
        branch = run_command(["git", "branch", "--show-current"])
        if branch:
            return branch
    except subprocess.CalledProcessError:
        pass

    # Fallback: find a remote branch that contains HEAD
    output = run_command(
        ["git", "branch", "--remote", "--verbose", "--no-abbrev", "--contains", "HEAD"]
    )
    for line in output.splitlines():
        line = line.strip()
        if "->" in line:
            continue
        # look like origin/branch
        m = re.match(r"^[^/]+/([^ ]+)", line)
        if m:
            return m.group(1)
    # Last resort
    return "HEAD"


def get_target_branch_from_env() -> Optional[str]:
    """
    Read MR target branch name from common CI environment variables.
    """
    return os.getenv("CI_MERGE_REQUEST_TARGET_BRANCH_NAME") or os.getenv(
        "TARGET_BRANCH"
    )


def ensure_fetch_master() -> None:
    """
    Ensure origin/master exists locally.
    """
    run_command(
        ["git", "fetch", "--no-tags", "origin", "master:refs/remotes/origin/master"]
    )


def get_merge_base_with_master(ref: str = "HEAD") -> str:
    """
    Return the merge-base commit hash between <ref> and origin/master.
    """
    return run_command(["git", "merge-base", ref, "origin/master"])


def last_version_in_commit_reachable_from(commit: str, version_in_path: str) -> str:
    """
    Return the last commit hash which modified VERSION.in reachable from `commit`.
    """
    return run_command(
        ["git", "log", commit, "--follow", "-1", "--pretty=%H", "--", version_in_path]
    )


def count_commits_between(older: str, newer: str) -> int:
    """
    Count commits reachable from `newer` but not from `older`.
    """
    return int(run_command(["git", "rev-list", "--count", f"{older}..{newer}"]))


def list_git_tags_matching(pattern: str) -> List[str]:
    """
    Return a list of tag names matching the given pattern.
    """
    out = run_command(["git", "tag", "--list", pattern])
    if not out:
        return []
    return [t.strip() for t in out.splitlines() if t.strip()]


def read_version_in_at_commit(
    merge_base: str, version_in_path: Path
) -> Tuple[int, int]:
    """
    Read VERSION.in as of commit `merge_base` using `git show`.
    Fallback to working-tree file if git show fails (defensive).
    """
    git_top = run_command(["git", "rev-parse", "--show-toplevel"])
    version_relative_path = str(
        version_in_path.resolve().relative_to(Path(git_top).resolve())
    )
    content = run_command(["git", "show", f"{merge_base}:{version_relative_path}"])
    txt = "".join(content.split())
    m = re.match(r"^(\d+)\.(\d+)$", txt)
    if not m:
        raise ValueError(f"VERSION.in format invalid (at {merge_base}): {txt!r}")
    return int(m.group(1)), int(m.group(2))


def compute_base_master_version_for_ref(
    ref: str, version_in_path: Path
) -> Tuple[int, int, int]:
    ensure_fetch_master()
    merge_base = get_merge_base_with_master(ref)
    major, minor = read_version_in_at_commit(merge_base, version_in_path)
    last_version_commit = last_version_in_commit_reachable_from(
        merge_base, version_in_path.as_posix()
    )
    patch = count_commits_between(last_version_commit, merge_base)
    return major, minor, patch


def compute_next_post_from_tags(base_version: str, tag_namespace: str = "helix") -> int:
    """
    Determine next post number for base_version by inspecting git tags:
      <tag_namespace>-<base_version>.post<N>
      <tag_namespace>-<base_version>-post<N>
    """
    pattern1 = f"{tag_namespace}-{base_version}.post*"
    pattern2 = f"{tag_namespace}-{base_version}-post*"
    tags = list_git_tags_matching(pattern1) + list_git_tags_matching(pattern2)
    max_post = 0
    regex = re.compile(
        rf"{re.escape(tag_namespace)}-{re.escape(base_version)}(?:\.post|-post)(\d+)$"
    )
    for t in tags:
        m = regex.search(t)
        if m:
            try:
                n = int(m.group(1))
            except ValueError:
                continue
            if n > max_post:
                max_post = n
    return max_post + 1


def format_pep440_post(base: str, post: int) -> str:
    """
    Format PEP440 post version: X.Y.Z.postN
    """
    return f"{base}.post{post}"


def get_short_sha(ref: str = "HEAD") -> str:
    """
    Return short SHA (7 characters) of given ref.
    """
    return run_command(["git", "rev-parse", "--short", ref])


def get_full_version() -> str:
    """Generate and return the full helix version string."""
    tag_ns = "helix"
    version_in = get_version_in_path()
    current_branch = get_current_branch()

    # CI running on helix (typical merge-to-helix job)
    if current_branch == "helix":
        final_version = _compute_helix_branch_version(tag_ns, version_in)
        return final_version

    # Not on helix branch
    target_branch = get_target_branch_from_env()
    if target_branch == "helix":
        return _compute_dev_branch_version(target_branch, tag_ns, version_in)

    # Neither on helix nor targeting helix -> warn and exit without computing
    raise RuntimeError(
        f"CI branch '{current_branch}' is not 'helix' and no target branch pointing to "
        f"'helix' was detected (target: {target_branch}). "
        "Not computing a helix version.",
    )


def _compute_helix_branch_version(tag_ns: str, version_in: Path) -> str:
    major, minor, patch = compute_base_master_version_for_ref("HEAD", version_in)
    base_version = f"{major}.{minor}.{patch}"
    next_post = compute_next_post_from_tags(base_version, tag_namespace=tag_ns)
    return format_pep440_post(base_version, next_post)


def _compute_dev_branch_version(
    target_branch: str, tag_ns: str, version_in: Path
) -> str:
    remote_ref = f"origin/{target_branch}"
    major, minor, patch = compute_base_master_version_for_ref(remote_ref, version_in)

    base_version = f"{major}.{minor}.{patch}"
    short_sha = get_short_sha("HEAD")
    # compute the next post slot (predictive)
    next_post = compute_next_post_from_tags(base_version, tag_namespace=tag_ns)
    return f"{format_pep440_post(base_version, next_post)}+{short_sha}"


def main():
    """Generate and print the full version string."""
    try:
        version = get_full_version()
        print(version)
        return 0
    except Exception as e:
        print(f"Error: Could not generate version number.\n{e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
else:
    # For hatch build integration
    __version__ = get_full_version()
