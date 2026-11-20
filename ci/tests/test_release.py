#  Copyright Contributors to the OpenCue Project
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

"""Tests for ci/release.py."""

import contextlib
import io
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

REPO = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO / "ci"))

import release  # pylint: disable=import-error,wrong-import-position

SHA = "a" * 40
OTHER_SHA = "b" * 40
BUILD_ID = "1.2.3"


def master_run(run_id, **fields):
    return {
        "id": run_id,
        "path": release.MASTER_WORKFLOW,
        "event": "push",
        "head_branch": "master",
        "head_sha": SHA,
        "status": "completed",
        "conclusion": "success",
        "run_attempt": 1,
        "html_url": f"https://github.com/o/r/actions/runs/{run_id}",
        **fields,
    }


def metadata(**fields):
    images = {
        name: {"tag": f"opencuebuild/{name}:{BUILD_ID}", "id": "sha256:" + str(i) * 64}
        for i, name in enumerate(release.IMAGES)
    }
    return {"git_commit": SHA, "build_id": BUILD_ID, "run_id": "7", "images": images, **fields}


def quiet():
    return contextlib.redirect_stdout(io.StringIO())


def git(cwd, *args):
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    ).stdout.strip()


class VersionTests(unittest.TestCase):
    def test_version_of(self):
        self.assertEqual("1.2.3", release.version_of("v1.2.3"))
        with self.assertRaisesRegex(release.ReleaseError, "not a release tag"):
            release.version_of("1.2.3")

    def test_is_newest(self):
        tags = ["v1.2.3", "v1.10.0", "v1.9.9", "v2.0.0-rc", "nightly"]
        self.assertTrue(release.is_newest("v1.10.0", tags))
        self.assertTrue(release.is_newest("v1.10.1", tags))
        self.assertFalse(release.is_newest("v1.9.9", tags))
        self.assertFalse(release.is_newest("v1.11.0-abc", tags))


class SelectMasterRunTests(unittest.TestCase):
    def test_newest_green_run(self):
        runs = [master_run(1), master_run(3, conclusion="failure"), master_run(2)]
        self.assertEqual(2, release.select_master_run(runs, SHA, True)["id"])

    def test_ignores_other_runs(self):
        runs = [
            master_run(1, path=".github/workflows/pr.yml"),
            master_run(2, event="workflow_dispatch"),
            master_run(3, head_branch="feature"),
            master_run(4, head_sha=OTHER_SHA),
        ]
        with self.assertRaisesRegex(release.ReleaseError, "No OpenCue Master run"):
            release.select_master_run(runs, SHA, True)

    def test_not_on_master(self):
        with self.assertRaisesRegex(release.ReleaseError, "is not on master"):
            release.select_master_run([], SHA, False)

    def test_in_progress(self):
        runs = [master_run(1, status="in_progress", conclusion=None)]
        with self.assertRaisesRegex(release.ReleaseError, "still in_progress.*runs/1. Wait"):
            release.select_master_run(runs, SHA, True)

    def test_failed(self):
        runs = [
            master_run(1, conclusion="failure"),
            master_run(2, conclusion="cancelled", run_attempt=2),
        ]
        with self.assertRaisesRegex(
            release.ReleaseError, r"concluded cancelled \(attempt 2\).*runs/2"
        ):
            release.select_master_run(runs, SHA, True)


class SelectBundleTests(unittest.TestCase):
    URL = "https://github.com/o/r/actions/runs/1"

    def test_live_bundle(self):
        artifacts = [
            {"id": 1, "name": "release-bundle", "expired": True, "expires_at": "x"},
            {"id": 2, "name": "release-bundle", "expired": False, "expires_at": "y"},
            {"id": 3, "name": "release-notes", "expired": False, "expires_at": "y"},
        ]
        self.assertEqual(2, release.select_bundle(artifacts, self.URL)["id"])

    def test_expired(self):
        artifacts = [
            {"id": 1, "name": "release-bundle", "expired": True, "expires_at": "2027-01-01"}
        ]
        with self.assertRaisesRegex(release.ReleaseError, "expired on 2027-01-01.*Tag a newer"):
            release.select_bundle(artifacts, self.URL)

    def test_missing(self):
        with self.assertRaisesRegex(release.ReleaseError, "has no release-bundle"):
            release.select_bundle([], self.URL)


class PreflightTests(unittest.TestCase):
    def test_run_id_only_for_dry_runs(self):
        with mock.patch.object(release, "resolve_commit", return_value=SHA):
            with self.assertRaisesRegex(release.ReleaseError, "only be given for a dry run"):
                release.preflight("o/r", "v1.2.3", "", "7", dry_run=False)

    def test_finds_run_and_bundle(self):
        responses = {
            f"repos/o/r/actions/runs?head_sha={SHA}&event=push&branch=master&per_page=100": {
                "workflow_runs": [master_run(7)]
            },
            "repos/o/r/actions/runs/7/artifacts?name=release-bundle": {
                "artifacts": [{"id": 9, "name": "release-bundle", "expired": False}]
            },
        }
        with mock.patch.object(release, "resolve_commit", return_value=SHA), mock.patch.object(
            release, "gh_api", side_effect=responses.__getitem__
        ), mock.patch.object(release, "run", return_value="v1.2.2\nv1.2.3"), quiet():
            outputs = release.preflight("o/r", "v1.2.3", "", "", dry_run=False)
        self.assertEqual(
            {
                "sha": SHA,
                "version": "1.2.3",
                "run-id": "7",
                "latest": "true",
                "run-url": "https://github.com/o/r/actions/runs/7",
            },
            outputs,
        )


class MetadataTests(unittest.TestCase):
    def test_matches(self):
        release.check_metadata(metadata(), BUILD_ID, SHA, 7)

    def test_wrong_commit(self):
        with self.assertRaisesRegex(release.ReleaseError, f"built from {OTHER_SHA}, not {SHA}"):
            release.check_metadata(metadata(git_commit=OTHER_SHA), BUILD_ID, SHA, "7")

    def test_wrong_run(self):
        with self.assertRaisesRegex(release.ReleaseError, "names run 8, not 7"):
            release.check_metadata(metadata(run_id="8"), BUILD_ID, SHA, "7")

    def test_tag_does_not_match_build(self):
        with self.assertRaisesRegex(
            release.ReleaseError, "Tag v1.2.4 does not match build ID 1.2.3.*as v1.2.3"
        ):
            release.check_metadata(metadata(), "1.2.4", SHA, "7")

    def test_images(self):
        data = metadata()
        data["images"]["rqd"]["tag"] = "opencuebuild/rqd:1.2.2"
        del data["images"]["cueweb"]
        with self.assertRaisesRegex(
            release.ReleaseError, "lists images.*rqd image is opencuebuild/rqd:1.2.2"
        ):
            release.check_metadata(data, BUILD_ID, SHA, "7")


class BundleTests(unittest.TestCase):
    def setUp(self):
        self.bundle = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.bundle)
        for name in [*release.github_assets(BUILD_ID), *release.pypi_files(BUILD_ID), "VERSION"]:
            (self.bundle / name).write_text("x")
        (self.bundle / "build_metadata.json").write_text(json.dumps(metadata()))

    def test_complete_bundle(self):
        # Also keeps the file lists here in line with ci/check_release_bundle.sh.
        with quiet():
            release.verify(self.bundle, "v1.2.3", SHA, "7")

    def test_incomplete_bundle(self):
        (self.bundle / "opencue_cuegui-1.2.3.tar.gz").unlink()
        with quiet(), self.assertRaisesRegex(
            release.ReleaseError, "Missing: opencue_cuegui-1.2.3.tar.gz"
        ):
            release.verify(self.bundle, "v1.2.3", SHA, "7")

    def test_plan(self):
        text = release.plan(self.bundle, "v1.2.3", "https://run", latest=True, publish=False)
        self.assertIn("## v1.2.3: dry run", text)
        self.assertIn("- `openrqd-1.2.3-x86_64-pc-windows-msvc.exe` (1 bytes)", text)
        self.assertIn(
            "`opencuebuild/cuebot:1.2.3` → `opencue/cuebot:1.2.3`, `opencue/cuebot:latest`", text
        )
        self.assertIn("- `opencue_pycue-1.2.3-py3-none-any.whl`", text)

    def test_branch_build_python_version(self):
        self.assertIn("opencue_rqd-1.2.3+abc.tar.gz", release.pypi_files("1.2.3-abc"))


class FakeDocker:
    """Answers imagetools inspect from a dict of tag to (manifest digest, config digest)."""

    def __init__(self, images, fail_create=()):
        self.images = images
        self.fail_create = fail_create
        self.created = []

    def __call__(self, *args):
        if args[:3] == ("buildx", "imagetools", "inspect"):
            if args[-1] not in self.images:
                raise subprocess.CalledProcessError(1, args, stderr="not found")
            manifest, config = self.images[args[-1]]
            if "--raw" in args:
                return json.dumps({"config": {"digest": config}})
            return json.dumps({"digest": manifest})
        if args[:3] == ("buildx", "imagetools", "create"):
            if any(name in args[-1] for name in self.fail_create):
                raise subprocess.CalledProcessError(1, args, stderr="denied")
            self.created.append(args[3:])
            return ""
        raise AssertionError(args)


class ImageTests(unittest.TestCase):
    def setUp(self):
        self.metadata = metadata()
        self.staged = {
            image["tag"]: ("sha256:m" + name, image["id"])
            for name, image in self.metadata["images"].items()
        }

    def test_retags_by_digest(self):
        docker = FakeDocker(self.staged)
        with quiet():
            release.retag_images(self.metadata, BUILD_ID, True, docker)
        self.assertIn(
            (
                "--prefer-index=false",
                "--tag=opencue/cuebot:1.2.3",
                "--tag=opencue/cuebot:latest",
                "opencuebuild/cuebot@sha256:mcuebot",
            ),
            docker.created,
        )
        self.assertEqual(4, len(docker.created))

    def test_without_latest(self):
        docker = FakeDocker(self.staged)
        with quiet():
            release.retag_images(self.metadata, BUILD_ID, False, docker)
        self.assertEqual(
            ("--prefer-index=false", "--tag=opencue/rqd:1.2.3", "opencuebuild/rqd@sha256:mrqd"),
            docker.created[1],
        )

    def test_accepts_manifest_digest_as_id(self):
        self.metadata["images"]["rqd"]["id"] = "sha256:mrqd"
        with quiet():
            release.retag_images(self.metadata, BUILD_ID, False, FakeDocker(self.staged))

    def test_required_image_missing_publishes_nothing(self):
        del self.staged["opencuebuild/rqd:1.2.3"]
        docker = FakeDocker(self.staged)
        with quiet(), self.assertRaisesRegex(
            release.ReleaseError, "Can't release opencuebuild/rqd"
        ):
            release.retag_images(self.metadata, BUILD_ID, True, docker)
        self.assertEqual([], docker.created)

    def test_changed_image_publishes_nothing(self):
        self.staged["opencuebuild/cuebot:1.2.3"] = ("sha256:new", "sha256:newconfig")
        docker = FakeDocker(self.staged)
        with quiet(), self.assertRaisesRegex(
            release.ReleaseError, "not the image .* that the build tested"
        ):
            release.retag_images(self.metadata, BUILD_ID, True, docker)
        self.assertEqual([], docker.created)

    def test_optional_images_warn(self):
        del self.staged["opencuebuild/cueweb:1.2.3"]
        docker = FakeDocker(self.staged, fail_create=["rest-gateway"])
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            release.retag_images(self.metadata, BUILD_ID, True, docker)
        self.assertEqual(2, len(docker.created))
        self.assertIn("::warning::Skipping opencuebuild/cueweb:1.2.3", output.getvalue())
        self.assertIn("::warning::Could not retag opencuebuild/rest-gateway@", output.getvalue())

    def test_required_retag_failure(self):
        docker = FakeDocker(self.staged, fail_create=["opencuebuild/cuebot"])
        with quiet(), self.assertRaisesRegex(
            release.ReleaseError, "Retagging opencuebuild/cuebot@.* denied"
        ):
            release.retag_images(self.metadata, BUILD_ID, True, docker)


class GitTests(unittest.TestCase):
    """Runs the git-based steps in a throwaway repository with an origin remote."""

    def setUp(self):
        tmp = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        origin = tmp / "origin"
        origin.mkdir()
        git(origin, "init", "-q", "-b", "master")
        git(origin, "config", "user.email", "test@example.com")
        git(origin, "config", "user.name", "Test")
        self.commits = []
        for i in range(4):
            git(origin, "commit", "-q", "--allow-empty", "-m", f"change {i}")
            self.commits.append(git(origin, "rev-parse", "HEAD"))
        git(origin, "tag", "v1.2.0", self.commits[0])
        git(origin, "tag", "-a", "-m", "release", "v1.2.3", self.commits[2])
        git(origin, "checkout", "-q", "-b", "unreleased")
        git(origin, "commit", "-q", "--allow-empty", "-m", "not on master yet")
        self.unfetched = git(origin, "rev-parse", "HEAD")
        git(origin, "checkout", "-q", "master")

        checkout = tmp / "checkout"
        git(tmp, "clone", "-q", "--single-branch", str(origin), str(checkout))
        cwd = os.getcwd()
        os.chdir(checkout)
        self.addCleanup(os.chdir, cwd)

    def test_annotated_tag(self):
        self.assertEqual(self.commits[2], release.resolve_commit("v1.2.3", "", False))

    def test_tag_and_sha_disagree(self):
        with self.assertRaisesRegex(release.ReleaseError, "v1.2.3 points at"):
            release.resolve_commit("v1.2.3", self.commits[1], False)

    def test_missing_tag(self):
        with self.assertRaisesRegex(release.ReleaseError, "Tag v9.9.9 does not exist. Push"):
            release.resolve_commit("v9.9.9", "", True)
        with self.assertRaisesRegex(release.ReleaseError, "only a dry run"):
            release.resolve_commit("v9.9.9", self.commits[3], False)

    def test_dry_run_fetches_untagged_commit(self):
        self.assertEqual(self.unfetched, release.resolve_commit("v9.9.9", self.unfetched, True))
        git(".", "cat-file", "-e", self.unfetched)

    def test_release_notes(self):
        notes = release.release_notes(self.commits[2])
        self.assertTrue(notes.startswith("To learn how to install"))
        self.assertTrue(
            notes.endswith(
                f"## Changes:\n\n* {self.commits[1]} change 1\n* {self.commits[2]} change 2\n"
            )
        )


if __name__ == "__main__":
    unittest.main()
