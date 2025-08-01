---
layout: default
title: "v0.22.14 release"
parent: Releases
nav_order: 3
---

# Announcing the release of OpenCue v0.22.14

### OpenCue v0.22.14 release notes

#### Thursday, July 13, 2023

---

[v0.22.14 of OpenCue](https://github.com/AcademySoftwareFoundation/OpenCue/releases/tag/v0.22.14)
includes the following changes and updates:

*   [rqd] Add some missing env vars on Windows. [#1225](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1225)
*   [cuebot] Fix malformed SQL queries. [#1222](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1222)
*   [rqd] Add pynput to requirements.txt. [#1230](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1230)
*   Upgrade PySide2 to 5.15.2.1. [#1226](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1226)
*   [sandbox] Stability improvements. [#1244](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1244)
*   Lock evdev dependency for Python 2. [#1248](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1248)
*   [rqd] Raise exception during startup if CUEBOT_HOSTNAME is empty. [#1237](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1237)
*   [cuebot] Fix a few database query and test issues. [#1232](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1232)
*   [cuegui] Move constants to a YAML config file. [#1242](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1242)
*   [rqd] Add new config option RQD_USE_PATH_ENV_VAR. [#1241](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1241)
*   [cuegui] Use the QtPy library instead of PySide directly. [#1238](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1238)
*   [pyoutline] Move outline.cfg into the outline module. [#1252](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1252)
*   Upgrade future to 0.18.3. [#1254](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1254)
*   [cuegui] Fix Comment dialog macros load and add tests. [#1261](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1261)
*   Prepend every rqd log line with a timestamp  [#1286](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1286)
*   Migrate stats columns from show to show_stats [#1228](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1228)