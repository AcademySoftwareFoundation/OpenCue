---
layout: default
title: "v0.2.145 release"
parent: Releases
nav_order: 15
---

# Announcing the release of OpenCue v0.2.145

### OpenCue v0.2.145 release notes

#### Friday, November 22, 2019

---

[v0.2.145 of OpenCue](https://github.com/AcademySoftwareFoundation/OpenCue/releases/tag/0.2.145)
includes the following changes and updates:

*   Reorganized packaging pipeline and locked image versions in [#542](https://github.com/AcademySoftwareFoundation/OpenCue/pull/542).
*   Updated CueGUI unit tests to run with Python 3 in its Dockerfile in [#538](https://github.com/AcademySoftwareFoundation/OpenCue/pull/538).
*   Added support to copy attributes when selected in [#525](https://github.com/AcademySoftwareFoundation/OpenCue/pull/525).
*   Added a connection exception and retries to the PyCue gRPC decorator in [#536](https://github.com/AcademySoftwareFoundation/OpenCue/pull/536).
*   Fixed a drag and drop in the CueGUI job monitor in [#512](https://github.com/AcademySoftwareFoundation/OpenCue/pull/512).
*   Added extra show filter options to MonitorCue in [#527](https://github.com/AcademySoftwareFoundation/OpenCue/pull/527).
*   Fixed retry all dead frames on a layer in [#514](https://github.com/AcademySoftwareFoundation/OpenCue/pull/514).
*   Added Cuebot and RQD Systemd service scripts in [#504](https://github.com/AcademySoftwareFoundation/OpenCue/pull/504).
*   Added wrapper function for chunk size on layer in [#520](https://github.com/AcademySoftwareFoundation/OpenCue/pull/520).
*   Added a double click to proc view in [#516](https://github.com/AcademySoftwareFoundation/OpenCue/pull/516).
*   Fixed a comment dropdown for PySide 2 in [#508](https://github.com/AcademySoftwareFoundation/OpenCue/pull/508).
*   Fixed incorrect function calls [#510](https://github.com/AcademySoftwareFoundation/OpenCue/pull/510).
*   Fixed the Blender argument ordering - current ordering caused output path to be overwritten - order matters for Blender in [#502](https://github.com/AcademySoftwareFoundation/OpenCue/pull/502).
*   Fixed layer dependency creation API typos [#498](https://github.com/AcademySoftwareFoundation/OpenCue/pull/498).
*   Fixed a couple syntax bugs with the Oracle queries in [#499](https://github.com/AcademySoftwareFoundation/OpenCue/pull/499).
*   Added a sample Dockerfile for Blender 2.79 on RQD [#496](https://github.com/AcademySoftwareFoundation/OpenCue/pull/496).
*   Added an exception when search args are not passed the correct type in [#489](https://github.com/AcademySoftwareFoundation/OpenCue/pull/489).
