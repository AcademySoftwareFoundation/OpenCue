#!/usr/bin/env python3

"""Promotes a green master build to a release, for .github/workflows/release.yml.

A release publishes the release-bundle artifact of the OpenCue Master run of the tagged
commit, and retags the images that run staged. Nothing is rebuilt.

  preflight  resolves the tag's commit, then finds its green master run and that run's bundle
  pinned     checks that the bundle preflight chose is still the run's bundle
  verify     checks a downloaded bundle against the tag, the commit and the run
  plan       prints what the release publishes, as Markdown
  notes      prints the release notes
  files      lists the bundle files published to GitHub or PyPI
  images     retags the staged images on Docker Hub
  github     says whether the GitHub release must be created, updated or left alone

`preflight` and `notes` need a clone with full history and tags. `preflight`, `pinned` and
`github` call the GitHub API through `gh` (GH_TOKEN with actions: read; `github` needs
contents: write to see draft releases). A failed check prints an ::error::
annotation that says what to do, and exits 1.
"""

import argparse
import json
import os
import pathlib
import re
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent

MASTER_WORKFLOW = ".github/workflows/master.yml"
BUNDLE = "release-bundle"

PYTHON_PACKAGES = [
    "proto", "pycue", "pyoutline", "cueadmin", "cueman", "cuecmd", "cuesubmit", "cuegui",
    "rqd", "cuenimby",
]
RUST_TARGETS = [
    "x86_64-unknown-linux-gnu", "x86_64-unknown-linux-musl", "x86_64-apple-darwin",
    "aarch64-apple-darwin",
]
WINDOWS_TARGET = "x86_64-pc-windows-msvc"

# Image name to whether it is optional: failing to retag an optional image is a warning, as
# master.yml's failure to stage it is.
IMAGES = {"cuebot": False, "rqd": False, "rest-gateway": True, "cueweb": True}

NOTES = """\
To learn how to install and configure OpenCue, see our \
[Getting Started guide](https://www.opencue.io/docs/getting-started/).

## Changes:

{commits}
"""


class ReleaseError(Exception):
    """A check failed. The message tells the release manager what to do."""


def run(*cmd):
    """Runs a command and returns its stripped stdout."""
    return subprocess.run(cmd, check=True, capture_output=True, text=True).stdout.strip()


def gh_api(path, paginate=False):
    """Calls the GitHub API. With paginate, returns the items of every page of a list."""
    args = ["--paginate", "--slurp"] if paginate else []
    try:
        result = json.loads(run("gh", "api", *args, path))
    except subprocess.CalledProcessError as e:
        raise ReleaseError(f"GitHub API call {path} failed: {e.stderr.strip()}") from e
    return [item for page in result for item in page] if paginate else result


def version_of(tag):
    """Returns the version a release tag names: v1.2.3 is 1.2.3."""
    if not tag.startswith("v") or len(tag) < 2:
        raise ReleaseError(f"{tag} is not a release tag. Release tags are v<version>, e.g. v1.2.3.")
    return tag[1:]


def release_version(tag):
    """Returns a vX.Y.Z tag's version as a tuple of ints, or None for any other tag."""
    match = re.fullmatch(r"v(\d+)\.(\d+)\.(\d+)", tag)
    return tuple(int(n) for n in match.groups()) if match else None


def latest_decision(tag, releases):
    """Returns whether `latest` moves to tag, and the reason when it doesn't.

    It moves unless a published (not draft, not pre-release) GitHub release has a higher
    vX.Y.Z tag. Only releases count, so a stray tag that never became one doesn't hold
    `latest` back.
    """
    version = release_version(tag)
    if version is None:
        return False, f"{tag} is not a vX.Y.Z release"
    higher = [
        r["tag_name"] for r in releases
        if not r["draft"] and not r["prerelease"]
        and (release_version(r["tag_name"]) or ()) > version
    ]
    if higher:
        return False, f"{max(higher, key=release_version)} is a higher published release"
    return True, ""


def resolve_commit(tag, sha, dry_run):
    """Returns the full commit SHA to release.

    That is the tag's commit. Only a dry run may name a commit for a tag that doesn't exist,
    to rehearse a release before tagging.
    """
    try:
        tagged = run("git", "rev-parse", "--verify", "--quiet", f"refs/tags/{tag}^{{commit}}")
    except subprocess.CalledProcessError:
        tagged = None
    if tagged:
        if sha and sha != tagged:
            raise ReleaseError(f"{tag} points at {tagged}, not {sha}.")
        return tagged
    if not sha:
        raise ReleaseError(f"Tag {tag} does not exist. Push the tag, then run the release.")
    if not dry_run:
        raise ReleaseError(
            f"Tag {tag} does not exist; only a dry run can release an untagged commit."
        )
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ReleaseError(f"{sha} is not a full commit SHA.")
    try:
        run("git", "cat-file", "-e", f"{sha}^{{commit}}")
    except subprocess.CalledProcessError:
        run("git", "fetch", "--quiet", "--no-tags", "origin", sha)
    return sha


def not_green(run_info):
    """Says why a master run that isn't green can't be released, and what to do."""
    url = run_info["html_url"]
    if run_info["status"] != "completed":
        return (
            f"The master run for this commit is still {run_info['status']}: {url}. "
            "Wait for it to finish green, then re-run this release."
        )
    return (
        f"The master run for this commit concluded {run_info['conclusion']} "
        f"(attempt {run_info['run_attempt']}): {url}. A release needs a green master run. "
        "If the failure is in CI rather than in the commit, re-run its failed jobs and then "
        "this release; otherwise fix master and tag the fixed commit."
    )


def select_master_run(runs, sha, on_master):
    """Returns the newest green OpenCue Master push run of sha among runs.

    on_master is whether master contains sha, and only words the message when there is no run.
    """
    runs = sorted(
        (
            r for r in runs
            if r["path"] == MASTER_WORKFLOW and r["event"] == "push"
            and r["head_branch"] == "master" and r["head_sha"] == sha
        ),
        key=lambda r: r["id"],
        reverse=True,
    )
    if not runs:
        if not on_master:
            raise ReleaseError(
                f"{sha} is not on master. Releases are cut from master: tag a master commit."
            )
        raise ReleaseError(
            f"No OpenCue Master run exists for {sha}. master.yml runs once per push, on the "
            "pushed head, so a commit in the middle of a multi-commit push, or one pushed "
            "before master.yml existed, has no run. Tag a master commit that has a green run."
        )
    for candidate in runs:
        if candidate["conclusion"] == "success":
            return candidate
    raise ReleaseError(not_green(runs[0]))


def select_bundle(artifacts, run_url):
    """Returns the run's unexpired release-bundle artifact."""
    bundles = [a for a in artifacts if a["name"] == BUNDLE]
    live = [a for a in bundles if not a["expired"]]
    if live:
        return max(live, key=lambda a: a["id"])
    if bundles:
        raise ReleaseError(
            f"The {BUNDLE} of {run_url} expired on {bundles[0]['expires_at']}; bundles are "
            "kept 90 days. Tag a newer master commit, whose run has a current bundle."
        )
    raise ReleaseError(f"{run_url} has no {BUNDLE} artifact, so it can't be released.")


def preflight(repo, tag, sha, run_id, dry_run):
    """Finds what to release. Returns the step outputs."""
    version = version_of(tag)
    sha = resolve_commit(tag, sha, dry_run)
    if run_id:
        if not dry_run:
            raise ReleaseError("A run ID may only be given for a dry run.")
        master_run = gh_api(f"repos/{repo}/actions/runs/{run_id}")
        if master_run["conclusion"] != "success":
            raise ReleaseError(not_green(master_run))
        print(
            f"::warning::Dry run from {master_run['html_url']} as given: its workflow, event, "
            "branch and commit are not checked."
        )
    else:
        runs = gh_api(
            f"repos/{repo}/actions/runs?head_sha={sha}&event=push&branch=master&per_page=100"
        )["workflow_runs"]
        on_master = bool(runs) or gh_api(f"repos/{repo}/compare/{sha}...master")["status"] in (
            "ahead", "identical",
        )
        master_run = select_master_run(runs, sha, on_master)
    artifacts = gh_api(f"repos/{repo}/actions/runs/{master_run['id']}/artifacts?name={BUNDLE}")
    bundle = select_bundle(artifacts["artifacts"], master_run["html_url"])
    print(f"Releasing {sha} as {tag} from {master_run['html_url']} (artifact {bundle['id']}).")
    latest, reason = latest_decision(tag, gh_api(f"repos/{repo}/releases?per_page=100", True))
    if not latest:
        print(f"::warning::opencue/*:latest is not moved: {reason}.")
    return {
        "sha": sha,
        "version": version,
        "run-id": str(master_run["id"]),
        "run-url": master_run["html_url"],
        "artifact-id": str(bundle["id"]),
        "artifact-digest": bundle.get("digest") or "",
        "latest": str(latest).lower(),
        "latest-reason": reason,
    }


def check_pinned(artifacts, artifact_id, digest, run_url):
    """Raises unless the artifact preflight chose is still the run's bundle, unchanged."""
    bundles = [a for a in artifacts if a["name"] == BUNDLE and not a["expired"]]
    if [(str(a["id"]), a.get("digest") or "") for a in bundles] != [(artifact_id, digest)]:
        found = ", ".join(f"{a['id']} ({a.get('digest')})" for a in bundles) or "none"
        raise ReleaseError(
            f"The {BUNDLE} of {run_url} changed after preflight: it chose artifact "
            f"{artifact_id} ({digest}), the run now has {found}. The master run was probably "
            "re-run. Re-run this whole release, so every job uses one bundle."
        )


def pinned(repo, run_id, artifact_id, digest):
    artifacts = gh_api(f"repos/{repo}/actions/runs/{run_id}/artifacts?name={BUNDLE}")
    check_pinned(artifacts["artifacts"], artifact_id, digest, f"run {run_id}")


def check_metadata(metadata, version, sha, run_id):
    """Raises unless build_metadata.json describes this commit, run and version."""
    problems = []
    build_id = metadata.get("build_id")
    if metadata.get("git_commit") != sha:
        problems.append(f"The bundle was built from {metadata.get('git_commit')}, not {sha}.")
    if str(metadata.get("run_id")) != str(run_id):
        problems.append(f"The bundle names run {metadata.get('run_id')}, not {run_id}.")
    if build_id != version:
        problems.append(
            f"Tag v{version} does not match build ID {build_id}, which master computed for "
            f"this commit. Move the tag: this commit releases as v{build_id}."
        )
    images = metadata.get("images", {})
    if sorted(images) != sorted(IMAGES):
        problems.append(f"The bundle lists images {sorted(images)}, not {sorted(IMAGES)}.")
    for name, image in images.items():
        if image.get("tag") != f"opencuebuild/{name}:{build_id}":
            problems.append(f"The {name} image is {image.get('tag')}, not from this build.")
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", image.get("id") or ""):
            problems.append(f"The {name} image has no image ID.")
    if problems:
        raise ReleaseError(" ".join(problems))


def verify(bundle, tag, sha, run_id):
    """Checks a downloaded bundle against its metadata and ci/check_release_bundle.sh."""
    version = version_of(tag)
    check_metadata(json.loads((bundle / "build_metadata.json").read_text()), version, sha, run_id)
    result = subprocess.run(
        [str(REPO / "ci" / "check_release_bundle.sh"), version, str(bundle)],
        capture_output=True, text=True, check=False,
    )
    print(result.stdout, end="")
    if result.returncode:
        raise ReleaseError(f"The bundle is incomplete: {' '.join(result.stdout.split())}")


def github_assets(build_id):
    """The bundle files attached to the GitHub release."""
    return [
        "LICENSE",
        f"schema-{build_id}.sql",
        f"seed_data-{build_id}.sql",
        f"cuebot-{build_id}-all.jar",
        f"opencue-cuebot-{build_id}-1.noarch.rpm",
        *(f"openrqd-{build_id}-{target}" for target in RUST_TARGETS),
        f"openrqd-{build_id}-{WINDOWS_TARGET}.exe",
    ]


def pypi_files(build_id):
    """The bundle's wheels and sdists, uploaded to PyPI."""
    version = build_id.replace("-", "+", 1)
    return [
        name
        for package in PYTHON_PACKAGES
        for name in (
            f"opencue_{package}-{version}-py3-none-any.whl", f"opencue_{package}-{version}.tar.gz"
        )
    ]


def image_targets(name, version, latest):
    return [f"opencue/{name}:{version}"] + ([f"opencue/{name}:latest"] if latest else [])


def pinned_source(image, docker):
    """Returns the staged image by digest, after checking it is the image the build recorded.

    The bundle records the image ID: the config digest, or with Docker's containerd image
    store, the manifest or index digest. An index (as the containerd store pushes) must hold
    exactly one image besides attestations, and that image's manifest or config digest counts.
    """
    inspect = ("buildx", "imagetools", "inspect")
    repository = image["tag"].rsplit(":", 1)[0]
    digest = json.loads(docker(*inspect, "--format", "{{json .Manifest}}", image["tag"]))["digest"]
    raw = json.loads(docker(*inspect, "--raw", image["tag"]))
    known = [digest]
    if "manifests" in raw:
        images = [
            m for m in raw["manifests"]
            if m.get("annotations", {}).get("vnd.docker.reference.type") != "attestation-manifest"
        ]
        if len(images) != 1:
            raise ReleaseError(
                f"{image['tag']} is an index of {len(images)} images, not one, so it can't be "
                "matched to the image the build tested."
            )
        child = json.loads(docker(*inspect, "--raw", f"{repository}@{images[0]['digest']}"))
        known += [images[0]["digest"], child.get("config", {}).get("digest")]
    else:
        known.append(raw.get("config", {}).get("digest"))
    if image["id"] not in known:
        raise ReleaseError(
            f"{image['tag']} is {digest} ({', '.join(map(str, known[1:]))}), not the image "
            f"{image['id']} that the build tested. Release from a new master run."
        )
    return f"{repository}@{digest}"


def retag_images(metadata, version, latest, docker):
    """Points opencue/<name>:<version> (and :latest) at the staged images, without pulling.

    Every required image is checked before any tag is written, so a missing or changed
    staged image publishes nothing.
    """
    sources = {}
    for name, optional in IMAGES.items():
        image = metadata["images"][name]
        try:
            sources[name] = pinned_source(image, docker)
        except (subprocess.CalledProcessError, ReleaseError) as e:
            if not optional:
                raise ReleaseError(f"Can't release {image['tag']}: {error_text(e)}") from e
            print(f"::warning::Skipping {image['tag']}, which is not released yet: {error_text(e)}")
    for name, source in sources.items():
        targets = image_targets(name, version, latest)
        # Without an index the release tag gets the staged manifest itself, digest and all.
        command = [
            "buildx", "imagetools", "create", "--prefer-index=false",
            *(f"--tag={t}" for t in targets), source,
        ]
        print(f"docker {' '.join(command)}")
        try:
            docker(*command)
        except subprocess.CalledProcessError as e:
            if not IMAGES[name]:
                raise ReleaseError(f"Retagging {source} failed: {error_text(e)}") from e
            print(f"::warning::Could not retag {source}, not released yet: {error_text(e)}")


def error_text(error):
    if isinstance(error, subprocess.CalledProcessError):
        return (error.stderr or "").strip() or str(error)
    return str(error)


def release_notes(sha):
    """Lists the commits since the previous release tag, as the GitHub release body."""
    previous = run("git", "describe", "--tags", "--abbrev=0", "--match", "v*", f"{sha}^")
    commits = run("git", "log", "--reverse", "--pretty=* %H %s", f"{previous}..{sha}")
    return NOTES.format(commits=commits)


def github_action(releases, tag):
    """Says what the release job does with the GitHub release of tag: create, update or keep.

    keep means it is published already, and publishing it is the release manager's call.
    """
    matches = [r for r in releases if r["tag_name"] == tag]
    if len(matches) > 1:
        ids = ", ".join(str(r["id"]) for r in matches)
        raise ReleaseError(f"{tag} has {len(matches)} releases ({ids}). Delete the extra drafts.")
    if not matches:
        return "create"
    return "update" if matches[0]["draft"] else "keep"


def plan(bundle, tag, run_url, latest, latest_reason, publish):
    """Describes what the release publishes, as Markdown."""
    version = version_of(tag)
    lines = [
        f"## {tag}: {'publishing' if publish else 'dry run, nothing is published'}",
        "",
        f"From {run_url}.",
        "",
        f"### GitHub release {tag} (draft)",
        "",
    ]
    lines += [f"- `{f}` ({(bundle / f).stat().st_size:,} bytes)" for f in github_assets(version)]
    lines += ["", "### Docker Hub", ""]
    for name, optional in IMAGES.items():
        targets = ", ".join(f"`{t}`" for t in image_targets(name, version, latest))
        note = " (optional)" if optional else ""
        lines.append(f"- `opencuebuild/{name}:{version}` → {targets}{note}")
    if not latest:
        lines += ["", f"`latest` is not moved: {latest_reason}."]
    lines += ["", "### PyPI", ""]
    lines += [f"- `{f}`" for f in pypi_files(version)]
    return "\n".join(lines) + "\n"


def set_outputs(outputs):
    for key, value in outputs.items():
        print(f"{key}={value}")
    if path := os.environ.get("GITHUB_OUTPUT"):
        with open(path, "a", encoding="utf-8") as f:
            f.writelines(f"{key}={value}\n" for key, value in outputs.items())


def docker_cli(*args):
    return run("docker", *args)


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)

    command = commands.add_parser("preflight")
    command.add_argument("--repo", required=True)
    command.add_argument("--tag", required=True)
    command.add_argument("--sha", default="")
    command.add_argument("--run-id", default="")
    command.add_argument("--dry-run", action="store_true")

    command = commands.add_parser("verify")
    command.add_argument("--tag", required=True)
    command.add_argument("--sha", required=True)
    command.add_argument("--run-id", required=True)
    command.add_argument("bundle", type=pathlib.Path)

    command = commands.add_parser("plan")
    command.add_argument("--tag", required=True)
    command.add_argument("--run-url", required=True)
    command.add_argument("--latest", action="store_true")
    command.add_argument("--latest-reason", default="")
    command.add_argument("--publish", action="store_true")
    command.add_argument("bundle", type=pathlib.Path)

    command = commands.add_parser("pinned")
    command.add_argument("--repo", required=True)
    command.add_argument("--run-id", required=True)
    command.add_argument("--artifact-id", required=True)
    command.add_argument("--digest", default="")

    command = commands.add_parser("github")
    command.add_argument("--repo", required=True)
    command.add_argument("--tag", required=True)

    command = commands.add_parser("notes")
    command.add_argument("--sha", required=True)

    command = commands.add_parser("files")
    command.add_argument("destination", choices=["github", "pypi"])
    command.add_argument("--tag", required=True)

    command = commands.add_parser("images")
    command.add_argument("--tag", required=True)
    command.add_argument("--latest", action="store_true")
    command.add_argument("metadata", type=pathlib.Path)

    return parser.parse_args(argv)


def main(argv):
    args = parse_args(argv)
    try:
        if args.command == "preflight":
            set_outputs(preflight(args.repo, args.tag, args.sha, args.run_id, args.dry_run))
        elif args.command == "verify":
            verify(args.bundle, args.tag, args.sha, args.run_id)
        elif args.command == "plan":
            text = plan(
                args.bundle, args.tag, args.run_url, args.latest, args.latest_reason, args.publish
            )
            print(text, end="")
        elif args.command == "pinned":
            pinned(args.repo, args.run_id, args.artifact_id, args.digest)
        elif args.command == "github":
            releases = gh_api(f"repos/{args.repo}/releases?per_page=100", paginate=True)
            print(github_action(releases, args.tag))
        elif args.command == "notes":
            print(release_notes(args.sha), end="")
        elif args.command == "files":
            files = github_assets if args.destination == "github" else pypi_files
            print("\n".join(files(version_of(args.tag))))
        elif args.command == "images":
            metadata = json.loads(args.metadata.read_text())
            retag_images(metadata, version_of(args.tag), args.latest, docker_cli)
    except ReleaseError as e:
        print(f"::error::{e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
