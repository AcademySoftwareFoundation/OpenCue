---
layout: default
title: "v0.1.107 release"
parent: Releases
nav_order: 21
---

# Announcing the release of OpenCue 0.1.107

### OpenCue v0.1.107 release notes

#### Tuesday, March 26, 2019

---

[v0.1.107 of OpenCue](https://github.com/AcademySoftwareFoundation/OpenCue/releases/tag/v0.1.107)
includes the following changes and updates:

*   [Pull request #226](https://github.com/AcademySoftwareFoundation/OpenCue/pull/226) - 
    Renamed PyOutline wrappers to follow OpenCue naming convention.
*   [Issue #248](https://github.com/AcademySoftwareFoundation/OpenCue/issues/248) -
    You can now configure the location of log directories by setting the `CUE_FRAME_LOG_DIR` environment
    variable on a Cuebot instance.
*   [Issue #237](https://github.com/AcademySoftwareFoundation/OpenCue/issues/237) - 
    Adds support to reuse existing gRPC connections between Cuebot and RQD.
*   [Issue #246](https://github.com/AcademySoftwareFoundation/OpenCue/issues/246) -
    Pycuerun no longer errors after submitting a job and prints submitted job IDs.
*   [Issue #176](https://github.com/AcademySoftwareFoundation/OpenCue/issues/176) -
    Docs now include system requirements for RQD and Cuebot.
*   [Issue #229](https://github.com/AcademySoftwareFoundation/OpenCue/issues/229) -
    You can now configure Pycue to randomly distribute loads across multiple Cuebot nodes.
*   [Issue #227](https://github.com/AcademySoftwareFoundation/OpenCue/issues/227) - 
    Fixes for CueGui monitor cue view.
