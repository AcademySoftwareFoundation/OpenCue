---
title: "Versioning"
nav_order: 14
parent: Concepts
layout: default
linkTitle: "Versioning"
date: 2020-04-10
description: >
  OpenCue policy on version number changes and compatibility between versions
---

# Versioning

### OpenCue policy on version number changes and compatibility between versions

---

This page defines the OpenCue policy on version number changes and compatibility between versions.

OpenCue version numbers contain three components: `<major>.<minor>.<patch>`.

- Major version will be incremented only by agreement of the technical steering committee (TSC).
  Major versions will be rare and the TSC will typically coordinate a list of new major features
  to be included. No compatibility should be assumed between major versions of OpenCue.

- Minor version will be incremented for potentially breaking changes. Users should not assume
  compatibility between minor versions of OpenCue.
  
  Examples of breaking changes include:
  - Database schema changes, as an un-updated Cuebot running old queries may fail.
  - Changes to the OpenCue proto files, as un-updated clients running previously valid API
    queries may fail.
   
- Patch version to be incremented on every commit merged to the OpenCue `master` branch.
  Patch versions with the same major and minor versions should be compatible with each other.
  
Developers and code reviewers should use their best judgement, but be prepared to revert a
commit and re-submit it with an incremented minor version if needed.

---

## How OpenCueWeb sources its version

OpenCueWeb participates in this shared versioning scheme rather than carrying a version of its own. The version it displays (in the bottom status bar and the **Help &rarr; About OpenCueWeb** dialog) is resolved **once at build time** and exposed to the client as `NEXT_PUBLIC_APP_VERSION`, using the first hit of this chain:

1. **`NEXT_PUBLIC_APP_VERSION`** (env var / Docker build-arg) - always wins. CI injects the generated OpenCue version or a Git SHA here.
2. **`cueweb/OVERRIDE_CUEWEB_VERSION.in`** - a small override file:
   - the default value, the sentinel `VERSION.in`, means "use the repo-root `VERSION.in`" - the same shared source of truth Cuebot and CueGUI read, so OpenCueWeb's number tracks the rest of OpenCue automatically;
   - any other value is used **verbatim**, letting a site pin an OpenCueWeb-specific version when it needs to.
3. **`package.json`** `version` - a last-resort fallback.

Separately, a **build SHA** is shown for provenance: it comes from the `NEXT_PUBLIC_GIT_SHA` build-arg (CI passes `git rev-parse --short HEAD`) and renders as `unknown` when not supplied.

**Why this design:** defaulting to the repo-root `VERSION.in` keeps OpenCueWeb consistent with OpenCue's policy above (no separate number to bump), while the override file and build-arg give deployments an explicit escape hatch when they need to label a build differently - without code changes.

> In the Docker image the repo-root `VERSION.in` lives outside OpenCueWeb's build context, so it is supplied through a `project_root` build context (see the OpenCueWeb deployment guide).
