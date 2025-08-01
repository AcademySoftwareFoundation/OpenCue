---
layout: default
title: "v0.3.33 release"
parent: Releases
nav_order: 13
---

# Announcing the release of OpenCue v0.3.33

### OpenCue v0.3.33 release notes

#### Wednesday, January 29, 2020

---

This release includes alpha-level support for Windows jobs and hosts. More
information on Windows support has been posted to the
[opencue-user mailing list](https://lists.aswf.io/g/opencue-user/topic/windows_support_alpha/70232740).

[v0.3.33 of OpenCue](https://github.com/AcademySoftwareFoundation/OpenCue/releases/tag/0.3.33)
includes the following changes and updates:

*   Add Python 3 support to RQD in [#573](https://github.com/AcademySoftwareFoundation/OpenCue/pull/573).
*   Add RQD Windows support in [#604](https://github.com/AcademySoftwareFoundation/OpenCue/pull/604).
*   Stop `qtimer` wrong thread segfault in [#598](https://github.com/AcademySoftwareFoundation/OpenCue/pull/598).
*   Stop and delete timer objects when attempting to close a window in [#596](https://github.com/AcademySoftwareFoundation/OpenCue/pull/596).
*   Add #OFRAME# (outframe) to `DispatchSupportService` to support chunks in [#597](https://github.com/AcademySoftwareFoundation/OpenCue/pull/597).
*   Set job back to pending in case of retry in [#517](https://github.com/AcademySoftwareFoundation/OpenCue/pull/517).
*   Upgrade `setuptools` in RQD docker in [#615](https://github.com/AcademySoftwareFoundation/OpenCue/pull/615).
*   Add dummy label to CueSubmit when there are no shows to solve in [#600](https://github.com/AcademySoftwareFoundation/OpenCue/pull/600).
*   Fix the permission check to include GID and UID in [#599](https://github.com/AcademySoftwareFoundation/OpenCue/pull/599).
*   Add retries to RQD gRPC startup in [#584](https://github.com/AcademySoftwareFoundation/OpenCue/pull/584).
*   Update Cuebot service definition to match new command line flags in [#581](https://github.com/AcademySoftwareFoundation/OpenCue/pull/581).
*   Allow CueGUI to create subscriptions larger than 50,000 in [#576](https://github.com/AcademySoftwareFoundation/OpenCue/pull/576).
