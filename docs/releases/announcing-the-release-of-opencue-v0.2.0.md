---
layout: default
title: "v0.2.0 release"
parent: Releases
nav_order: 19
---

# Announcing the release of OpenCue v0.2.0

### OpenCue v0.2.0 release notes

#### Wednesday, April 3, 2019

---

Make sure you update PyCue, CueGUI, and Cuebot, as there are API changes that
aren't compatible with older versions.

[v0.2.0 of OpenCue](https://github.com/AcademySoftwareFoundation/OpenCue/releases/tag/v0.2.0)
includes the following changes and updates:

*   [Issue #256](https://github.com/AcademySoftwareFoundation/OpenCue/issues/256) -
    Creates a CueSubmit config file, where you can specify values from
    `Constants.py`.
*   [Pull Request #261](https://github.com/AcademySoftwareFoundation/OpenCue/pull/261) -
    Update demo data to increase the default size limits on subscriptions
    and testing show.
*   [Issue #252](https://github.com/AcademySoftwareFoundation/OpenCue/issues/252)
    Expose Cuebot dispatcher settings in `opencue.properties` and disable
    the job lock by default, which dramatically speeds up the speed of the
    dispatcher.
*   [Issue #262](https://github.com/AcademySoftwareFoundation/OpenCue/issues/262)
    Update the styling of CueGUI on Linux operating systems.
*   [Issue #251](https://github.com/AcademySoftwareFoundation/OpenCue/issues/251)
    Increase the max gRPC message size to 100MB and update `getJobWhiteboard`
    to only return references to jobs.
*   [Issue #266](https://github.com/AcademySoftwareFoundation/OpenCue/issues/266)
    Cuebot: Use root locale when formatting number strings.
