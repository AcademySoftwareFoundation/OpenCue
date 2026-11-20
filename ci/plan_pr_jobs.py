#!/usr/bin/env python3

"""Decides which pull request jobs run, from the filters in .github/path-filters.yml.

Run by the `changes` job in .github/workflows/pr.yml after dorny/paths-filter. It reads the
filter step's outputs as JSON (with list-files: json) from stdin, and from the environment:

  LABELS          the pull request's label names as a JSON array
  CHANGED_FILES   the pull request's changed file count, to detect a truncated file list

and writes one output per job to GITHUB_OUTPUT and a summary to GITHUB_STEP_SUMMARY.

A change matched by the `ci` filter, the ci:full label, a changed file that no filter
matches, or a file list that may be truncated (the files API stops at 3000) turns every
job on.
"""

import json
import os
import pathlib
import re
import sys
import tomllib

REPO = pathlib.Path(__file__).resolve().parent.parent

FULL_LABEL = "ci:full"

# The most files the pull request files API lists.
FILES_API_LIMIT = 3000

PYTHON_PACKAGES = [
    "pycue", "pyoutline", "cueadmin", "cueman", "cuecmd", "cuesubmit", "cuegui", "cuenimby",
    "rqd",
]

# Tested in the aswf/ci-opencue container, which has Qt and xvfb.
QT_PACKAGES = {"cuegui", "cuesubmit"}

# Job outputs that are switched on by any of these filters.
JOB_FILTERS = {
    "wheels": {"packaging", "proto"},
    "licenses": {"packaging"},
    # The API reference autodocs pycue, pyoutline and proto, with warnings as errors.
    "api_docs": {"api-docs", "py-pycue", "py-pyoutline", "proto"},
    "cuebot": {"cuebot", "proto"},
    "maestro": {"scheduler"},
    "rust": {"rust", "proto"},
    "rust_windows": {"rqd", "proto"},
    "cueweb": {"cueweb"},
    "gateway": {"gateway", "proto"},
    "integration": {"integration", "proto"},
}


def local_dependencies(package):
    """Returns the OpenCue packages (by directory name) that a package depends on."""
    with open(REPO / package / "pyproject.toml", "rb") as f:
        dependencies = tomllib.load(f)["project"].get("dependencies", [])
    return {m.group(1) for d in dependencies if (m := re.match(r"opencue[-_](\w+)", d))}


def python_packages(changed):
    """Returns the Python packages to test: the changed ones and everything depending on them.

    `changed` holds directory names and may include `proto`, which every package builds on.
    """
    dependencies = {p: local_dependencies(p) for p in PYTHON_PACKAGES}

    def affected(package):
        return package in changed or any(affected(d) for d in dependencies.get(package, ()))

    return [p for p in PYTHON_PACKAGES if affected(p)]


def plan(filter_outputs, labels, changed_count=0):
    """Returns (job outputs, unmapped files, full) for a set of dorny/paths-filter outputs.

    `changed_count` is the pull request's changed file count, to detect a truncated file list.
    """
    matched = set(json.loads(filter_outputs["changes"]))
    files = {
        name.removesuffix("_files"): set(json.loads(value))
        for name, value in filter_outputs.items()
        if name.endswith("_files")
    }
    changed = files.pop("all")
    unmapped = sorted(changed - set().union(*files.values()))
    full = (
        "ci" in matched or FULL_LABEL in labels or bool(unmapped)
        or truncated(changed, changed_count)
    )

    if full:
        packages = PYTHON_PACKAGES
    else:
        changed_packages = {n.removeprefix("py-") for n in matched if n.startswith("py-")}
        if "proto" in matched:
            changed_packages.add("proto")
        packages = python_packages(changed_packages)

    jobs = {
        "python": json.dumps([p for p in packages if p not in QT_PACKAGES]),
        "python_qt": json.dumps([p for p in packages if p in QT_PACKAGES]),
    }
    for job, filters in JOB_FILTERS.items():
        jobs[job] = json.dumps(full or bool(matched & filters))
    return jobs, unmapped, full


def truncated(changed, changed_count):
    """Says whether the filter may have missed files.

    A rename is listed under both its paths, so only the count shows a list over the limit.
    """
    return changed_count > len(changed) or changed_count > FILES_API_LIMIT


def escape_command(value):
    return value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def main():
    labels = json.loads(os.environ.get("LABELS") or "[]")
    changed_count = int(os.environ.get("CHANGED_FILES") or 0)
    filter_outputs = json.load(sys.stdin)
    jobs, unmapped, full = plan(filter_outputs, labels, changed_count)

    if truncated(set(json.loads(filter_outputs["all_files"])), changed_count):
        print(f"::warning::The pull request changes {changed_count} files and its file list "
              "may be truncated, so every job runs.")

    for path in unmapped:
        print(escape_command(
            f"::warning::No filter in .github/path-filters.yml matches {path}, "
            "so every job runs. Add it to a filter."))

    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as out:
        out.write(f"full={json.dumps(full)}\n")
        for job, value in jobs.items():
            out.write(f"{job}={value}\n")

    summary = ["| Job | Runs |", "| --- | --- |"]
    summary += [f"| {job} | {value} |" for job, value in jobs.items()]
    if full:
        summary.insert(0, "Every job runs: CI files changed, the ci:full label is set, "
                          "a changed file is unmapped, or the file list was truncated.\n")
    with open(os.environ.get("GITHUB_STEP_SUMMARY", os.devnull), "a", encoding="utf-8") as f:
        f.write("\n".join(summary) + "\n")
    print("\n".join(summary))


if __name__ == "__main__":
    sys.exit(main())
