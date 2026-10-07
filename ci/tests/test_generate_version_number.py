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

"""Tests for the version number scripts in ci/."""

import pathlib
import platform
import shutil
import subprocess
import tempfile
import unittest

CI_DIR = pathlib.Path(__file__).resolve().parent.parent
SCRIPTS = ["generate_version_number.py", "generate_version_number.sh"]


def git(cwd, *args):
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    ).stdout.strip()


class GenerateVersionNumberTests(unittest.TestCase):
    """Runs the scripts against a throwaway repository with an origin remote."""

    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        origin = self.tmp / "origin.git"
        git(self.tmp, "init", "-q", "--bare", str(origin))
        git(origin, "symbolic-ref", "HEAD", "refs/heads/master")

        author = self.tmp / "author"
        git(self.tmp, "clone", "-q", str(origin), str(author))
        git(author, "config", "user.email", "test@example.com")
        git(author, "config", "user.name", "Test")
        git(author, "checkout", "-q", "-b", "master")
        (author / "ci").mkdir()
        for script in SCRIPTS:
            shutil.copy2(CI_DIR / script, author / "ci" / script)
        (author / "VERSION.in").write_text("1.2\n")
        git(author, "add", ".")
        git(author, "commit", "-q", "-m", "version")
        for i in range(3):
            git(author, "commit", "-q", "--allow-empty", "-m", f"change {i}")
        git(author, "tag", "v1.2.3")
        git(author, "push", "-q", "origin", "master", "v1.2.3")

        # A branch opened after the release commit, sorting before "master", that also
        # contains it (e.g. a dependabot branch).
        git(author, "checkout", "-q", "-b", "dependabot/bump")
        git(author, "commit", "-q", "--allow-empty", "-m", "bump")
        git(author, "push", "-q", "origin", "dependabot/bump")

        self.checkout = self.tmp / "checkout"
        git(self.tmp, "clone", "-q", str(origin), str(self.checkout))

    def run_script(self, script):
        return subprocess.run(
            [str(self.checkout / "ci" / script)],
            cwd=self.checkout,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    def assert_version(self, expected):
        self.assertEqual(expected, self.run_script("generate_version_number.py"))
        sed = "gsed" if platform.system() == "Darwin" else "sed"
        if shutil.which(sed):
            self.assertEqual(expected, self.run_script("generate_version_number.sh"))

    def test_master_branch(self):
        self.assert_version("1.2.3")

    def test_detached_tag_on_master_with_other_branches_containing_it(self):
        git(self.checkout, "checkout", "-q", "--detach", "v1.2.3")
        self.assert_version("1.2.3")

    def test_detached_commit_off_master(self):
        git(self.checkout, "checkout", "-q", "--detach", "origin/dependabot/bump")
        short_hash = git(self.checkout, "rev-parse", "--short", "HEAD")
        self.assertEqual(
            f"1.2.4-{short_hash}", self.run_script("generate_version_number.py")
        )


if __name__ == "__main__":
    unittest.main()
