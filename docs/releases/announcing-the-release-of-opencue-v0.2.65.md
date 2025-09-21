---
layout: default
title: "v0.2.65 release"
parent: Releases
nav_order: 17
---

# Announcing the release of OpenCue v0.2.65

### OpenCue v0.2.65 release notes

#### Wednesday, July 24, 2019

---

[v0.2.65 of OpenCue](https://github.com/AcademySoftwareFoundation/OpenCue/releases/tag/0.2.65)
includes the following changes and updates:

*   Added Blender as an option to CueSubmit in [#381](https://github.com/AcademySoftwareFoundation/OpenCue/pull/378).
*   Set up CI with Azure Pipelines in [#379](https://github.com/AcademySoftwareFoundation/OpenCue/pull/379).
*   Added a GitHub Pull Request template in [#376](https://github.com/AcademySoftwareFoundation/OpenCue/pull/376).
*   Updated `HostSearch` to return wrapped objects instead of Response class in [#373](https://github.com/AcademySoftwareFoundation/OpenCue/pull/373).
*   Changes to include `LICENSE` file in all Python tarballs and publish it alongside the other build artifacts in [#375](https://github.com/AcademySoftwareFoundation/OpenCue/pull/375).
*   Changes to ensure `ElementTree.SubElement` receives a `str` in [#369](https://github.com/AcademySoftwareFoundation/OpenCue/pull/369) to fix [#368](https://github.com/AcademySoftwareFoundation/OpenCue/issues/368).
*   Added missing wrapper function for `RegisterOutputPath` in [#363](https://github.com/AcademySoftwareFoundation/OpenCue/pull/363).
*   Updated `Submit.py` to honor the user-specified 'Chunk Size' value in [#366](https://github.com/AcademySoftwareFoundation/OpenCue/pull/366) to fix [#365](https://github.com/AcademySoftwareFoundation/OpenCue/issues/365).
*   Added owner and deed wrappers in [#362](https://github.com/AcademySoftwareFoundation/OpenCue/pull/362).
*   Migrated RQD unit tests to use `setup.py` in [#352](https://github.com/AcademySoftwareFoundation/OpenCue/pull/352).
*   Updated `Constants.py` in [#326](https://github.com/AcademySoftwareFoundation/OpenCue/pull/326) and [#353](https://github.com/AcademySoftwareFoundation/OpenCue/pull/353) to fix [#309](https://github.com/AcademySoftwareFoundation/OpenCue/issues/309).
*   Added a first few CueSubmit unit tests in [#346](https://github.com/AcademySoftwareFoundation/OpenCue/pull/346).
*   Added missing columns from query to fix `getHostWhiteboard` call in [#341](https://github.com/AcademySoftwareFoundation/OpenCue/pull/341).
*   Fixed the **Make a suggestion** CueGUI link in [#336](https://github.com/AcademySoftwareFoundation/OpenCue/pull/336).
*   Made `frameStateTotals` return a dictionary so order doesn't matter in [#331](https://github.com/AcademySoftwareFoundation/OpenCue/pull/331) to fix [#327](https://github.com/AcademySoftwareFoundation/OpenCue/issues/327).
