---
title: "Versioning"
nav_order: 9
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
