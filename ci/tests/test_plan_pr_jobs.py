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

"""Tests for ci/plan_pr_jobs.py and .github/path-filters.yml."""

import json
import pathlib
import re
import subprocess
import sys
import unittest

if sys.version_info < (3, 11):
    raise unittest.SkipTest("plan_pr_jobs.py needs tomllib (Python 3.11)")

REPO = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO / "ci"))

import plan_pr_jobs  # pylint: disable=import-error,wrong-import-position

FILTERS_FILE = REPO / ".github" / "path-filters.yml"
PR_WORKFLOW = REPO / ".github" / "workflows" / "pr.yml"
MASTER_WORKFLOW = REPO / ".github" / "workflows" / "master.yml"


def load_filters():
    """Parses path-filters.yml, which only holds lists of quoted patterns."""
    filters = {}
    for line in FILTERS_FILE.read_text().splitlines():
        if name := re.match(r"^([\w-]+):\s*$", line):
            patterns = filters.setdefault(name.group(1), [])
        elif pattern := re.match(r'^\s+-\s+"(.+)"\s*$', line):
            patterns.append(pattern.group(1))
    return filters


def glob_regex(pattern):
    """Translates the subset of picomatch globs used in path-filters.yml."""
    regex, i = "", 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            regex, i = regex + "(?:.*/)?", i + 3
        elif pattern.startswith("**", i):
            regex, i = regex + ".*", i + 2
        elif pattern[i] == "*":
            regex, i = regex + "[^/]*", i + 1
        else:
            regex, i = regex + re.escape(pattern[i]), i + 1
    return re.compile(regex + r"\Z")


def matches(patterns, path):
    """Matches like dorny/paths-filter with predicate-quantifier: some-with-excludes."""
    include = [p for p in patterns if not p.startswith("!")]
    exclude = [p[1:] for p in patterns if p.startswith("!")]
    return (any(glob_regex(p).match(path) for p in include)
            and not any(glob_regex(p).match(path) for p in exclude))


FILTERS = load_filters()


def filter_outputs(*paths):
    """Builds the outputs dorny/paths-filter would give for these changed files."""
    outputs = {}
    for name, patterns in FILTERS.items():
        matched = [p for p in paths if matches(patterns, p)]
        outputs[name] = json.dumps(bool(matched))
        outputs[f"{name}_files"] = json.dumps(matched)
    outputs["changes"] = json.dumps([n for n in FILTERS if outputs[n] == "true"])
    return outputs


def jobs_for(*paths, labels=()):
    jobs, _, _ = plan_pr_jobs.plan(filter_outputs(*paths), list(labels))
    return {job for job, value in jobs.items() if value not in ("false", "[]")}, jobs


ALL_JOBS = {"python", "python_qt", *plan_pr_jobs.JOB_FILTERS}


class PathFiltersTests(unittest.TestCase):

    def test_every_tracked_file_is_mapped(self):
        try:
            tracked = subprocess.run(["git", "ls-files"], cwd=REPO, check=True,
                                     capture_output=True, text=True).stdout.splitlines()
        except (OSError, subprocess.CalledProcessError):
            self.skipTest("not a git checkout")
        mapped = [patterns for name, patterns in FILTERS.items() if name != "all"]
        unmapped = [p for p in tracked if not any(matches(f, p) for f in mapped)]
        self.assertEqual([], unmapped, "add these paths to .github/path-filters.yml")

    def test_filters_and_plan_agree(self):
        used = {"ci", "all", "proto"} | set().union(*plan_pr_jobs.JOB_FILTERS.values())
        used |= {f"py-{p}" for p in plan_pr_jobs.PYTHON_PACKAGES}
        self.assertEqual(used | {"untested"}, set(FILTERS))

    def test_pr_workflow_uses_every_planner_output(self):
        workflow = PR_WORKFLOW.read_text()
        self.assertEqual(ALL_JOBS, set(re.findall(r"needs\.changes\.outputs\.(\w+)", workflow)))
        self.assertEqual(ALL_JOBS, set(re.findall(r"steps\.plan\.outputs\.(\w+)", workflow)))

    def test_master_workflow_tests_every_python_package(self):
        workflow = MASTER_WORKFLOW.read_text()
        packages = json.loads(re.search(r"^\s+packages: '(.+)'$", workflow, re.M).group(1))
        qt = json.loads(re.search(r"^\s+qt-packages: '(.+)'$", workflow, re.M).group(1))
        self.assertEqual(plan_pr_jobs.QT_PACKAGES, set(qt))
        self.assertEqual(plan_pr_jobs.PYTHON_PACKAGES,
                         [p for p in plan_pr_jobs.PYTHON_PACKAGES if p in packages + qt])
        self.assertEqual(len(plan_pr_jobs.PYTHON_PACKAGES), len(packages + qt))
        self.assertFalse(set(packages) & plan_pr_jobs.QT_PACKAGES)

    def test_glob_regex(self):
        self.assertTrue(matches(["**/Dockerfile*"], "Dockerfile"))
        self.assertTrue(matches(["**/Dockerfile*"], "rust/Dockerfile.rqd"))
        self.assertTrue(matches(["*.md"], "README.md"))
        self.assertFalse(matches(["*.md"], "docs/README.md"))
        self.assertTrue(matches(["sandbox/**", "!sandbox/maestro-sim/**"], "sandbox/a.sh"))
        self.assertFalse(matches(["sandbox/**", "!sandbox/maestro-sim/**"],
                                 "sandbox/maestro-sim/simulate.py"))


class PlanTests(unittest.TestCase):

    def test_docs_only_runs_nothing(self):
        self.assertEqual(set(), jobs_for("docs/_docs/index.md", "README.md")[0])

    def test_cueweb_only(self):
        self.assertEqual({"cueweb"}, jobs_for("cueweb/app/page.tsx")[0])

    def test_cuebot_outside_scheduler(self):
        self.assertEqual({"cuebot"}, jobs_for("cuebot/src/main/java/A.java")[0])

    def test_scheduler_runs_maestro(self):
        path = "cuebot/src/main/java/com/imageworks/spcue/dispatcher/Dispatcher.java"
        self.assertEqual({"cuebot", "maestro"}, jobs_for(path)[0])

    def test_maestro_sim_does_not_run_integration(self):
        self.assertEqual({"maestro"}, jobs_for("sandbox/maestro-sim/simulate.py")[0])

    def test_rust_outside_rqd_skips_windows(self):
        self.assertEqual({"rust"}, jobs_for("rust/crates/cueadmin/src/main.rs")[0])

    def test_rqd_runs_windows(self):
        self.assertEqual({"rust", "rust_windows"}, jobs_for("rust/crates/rqd/src/main.rs")[0])

    def test_rqd_dockerfile_runs_integration(self):
        self.assertEqual({"rust", "integration"}, jobs_for("rust/Dockerfile.rqd")[0])

    def test_cuebot_packaging_builds_the_rpm(self):
        for path in ("cuebot/packaging/rpm/cuebot.spec", "cuebot/deploy/opencue-cuebot"):
            self.assertEqual({"cuebot", "integration", "cuebot_packages"}, jobs_for(path)[0])
        self.assertIn("cuebot_packages", jobs_for("cuebot/Dockerfile")[0])
        self.assertEqual({"integration", "cuebot_packages"}, jobs_for("LICENSE")[0])
        self.assertNotIn("cuebot_packages", jobs_for("cuebot/src/main/java/A.java")[0])

    def test_single_python_package(self):
        names, jobs = jobs_for("cueadmin/cueadmin/common.py")
        self.assertEqual({"python"}, names)
        self.assertEqual(["cueadmin", "cueman"], json.loads(jobs["python"]))

    def test_python_dependents(self):
        _, jobs = jobs_for("pyoutline/outline/layer.py")
        self.assertEqual(["pyoutline", "cuecmd"], json.loads(jobs["python"]))
        self.assertEqual(["cuesubmit"], json.loads(jobs["python_qt"]))

    def test_pycue_runs_its_dependents(self):
        _, jobs = jobs_for("pycue/opencue/api.py")
        self.assertEqual(["pycue", "pyoutline", "cueadmin", "cueman", "cuecmd", "cuenimby"],
                         json.loads(jobs["python"]))
        self.assertEqual(["cuesubmit", "cuegui"], json.loads(jobs["python_qt"]))

    def test_api_docs_follow_autodoc_packages(self):
        self.assertEqual({"api_docs"}, jobs_for("api_docs/index.rst")[0])
        self.assertIn("api_docs", jobs_for("pycue/FileSequence/__init__.py")[0])
        self.assertIn("api_docs", jobs_for("pyoutline/outline/layer.py")[0])
        self.assertIn("api_docs", jobs_for("proto/src/job.proto")[0])
        self.assertNotIn("api_docs", jobs_for("cueadmin/cueadmin/common.py")[0])

    def test_autodoc_modules_are_covered(self):
        modules = set()
        for rst in (REPO / "api_docs").rglob("*.rst"):
            modules |= set(re.findall(r"automodule::\s+(\w+)", rst.read_text()))
        self.assertEqual({"opencue", "FileSequence", "outline", "opencue_proto"}, modules)

    def test_pyproject_runs_licenses_and_wheels(self):
        self.assertEqual({"python", "licenses", "wheels"},
                         jobs_for("cuenimby/pyproject.toml")[0])

    def test_proto(self):
        names, jobs = jobs_for("proto/src/job.proto")
        self.assertEqual(ALL_JOBS - {"licenses", "maestro", "cueweb", "cuebot_packages"}, names)
        self.assertEqual(len(plan_pr_jobs.PYTHON_PACKAGES),
                         len(json.loads(jobs["python"]) + json.loads(jobs["python_qt"])))

    def test_ci_runs_everything(self):
        self.assertEqual(ALL_JOBS, jobs_for(".github/workflows/pr.yml")[0])
        self.assertEqual(ALL_JOBS, jobs_for(".github/path-filters.yml")[0])
        self.assertEqual(ALL_JOBS, jobs_for("ci/run_python_lint.sh")[0])

    def test_full_label_runs_everything(self):
        self.assertEqual(ALL_JOBS, jobs_for("docs/index.md", labels=["ci:full"])[0])

    def test_truncated_file_list_runs_everything(self):
        outputs = filter_outputs("docs/index.md")
        _, _, full = plan_pr_jobs.plan(outputs, [], changed_count=1)
        self.assertFalse(full)
        jobs, _, full = plan_pr_jobs.plan(outputs, [], changed_count=3001)
        self.assertTrue(full)
        self.assertNotIn("false", jobs.values())

    def test_renames_cannot_hide_a_truncated_file_list(self):
        # The API listed 3000 files; a rename among them gives the filter 3001 paths.
        paths = [f"docs/{i}.md" for i in range(3001)]
        _, _, full = plan_pr_jobs.plan(filter_outputs(*paths), [], changed_count=3001)
        self.assertTrue(full)

    def test_unmapped_file_runs_everything(self):
        outputs = filter_outputs("newdir/thing.py")
        jobs, unmapped, full = plan_pr_jobs.plan(outputs, [])
        self.assertTrue(full)
        self.assertEqual(["newdir/thing.py"], unmapped)
        self.assertNotIn("false", jobs.values())


if __name__ == "__main__":
    unittest.main()
