---
layout: default
title: "v0.21.13 release"
parent: Releases
nav_order: 4
---

# Announcing the release of OpenCue v0.21.13

### OpenCue v0.21.13 release notes

#### Monday, January 9, 2023

---

[v0.21.13 of OpenCue](https://github.com/AcademySoftwareFoundation/OpenCue/releases/tag/v0.21.13)
includes the following changes and updates:

*   [cuegui] Fix NIMBY lock and refactor Nimby to Factory [#1106](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1106)
*   [cuebot] Post jobs should inherit parent environment variables [#1107](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1107)
*   [cuebot] Add balanced mode to dispatch query [#1103](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1103)
*   [cuegui] Swap RE with empty string in MonitorJobPlugin [#1132](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1132)
*   [cuegui] Update CueJobMonitorTree only with new data [#1128](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1128)
*   [cuebot] setChannel log supports old Python versions [#1126](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1126)
*   [cuebot] Add Proc's child PIDs to Host report stats [#1130](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1130)
*   [cuegui] Add kill dependent and group dependent features [#1115](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1115)
*   [cuebot] Support different logging paths based on OS [#1133](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1133)
*   [metrics] Add Limits info to Prometheus. [#1147](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1147)
*   [cuegui] Fix cue monitor gpu min/max. [#1144](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1144)
*   [cuebot] Add LluTime field in WhiteboardDaoJdbc.FRAME_MAPPER. [#1146](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1146)
*   [rqd] Adjust shutdown behavior and use Nimby pynput as default. [#1142](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1142)
*   [cuegui] New stuck frame plugin [#1120](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1120)
*   [cuegui] Improvements and new features for the Redirect plugin. [#1113](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1113)
*   Add more exit codes to Frame state waiting [#1131](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1131)
*   [cuegui] MonitorCue displays all jobs/groups to move. [#979](https://github.com/AcademySoftwareFoundation/OpenCue/pull/979)
*   [cuebot] Fix gRPC GetHost method. [#1148](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1148)
*   [cuebot] Add scheduled task to update show statuses [#1151](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1151)
*   [cuegui] Convert log paths between OSs [#1138](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1138)
*   [rqd] Fix None.shutdown bug on rqd [#1145](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1145)
*   [cuebot] Create feature flag to allow deeding [#1114](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1114)
*   [cuegui] Improve view running procs [#1141](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1141)
*   [cuegui] Remove invalid menu action. [#1154](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1154)
*   Add layer max cores. [#1125](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1125)
*   [cuebot] Fix PSQL Booking Next Frame RE word boundary match [#1078](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1078)
*   [cuebot] Add error handling for host allocation failures [#1149](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1149)
*   [cuebot] Fix bug affecting REBOOT_WHEN_IDLE hosts [#1153](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1153)
*   [cuegui] fix job monitor filter behavior [#1139](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1139)
*   [rqd] Core affinity for cache optimization [#1171](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1171)
*   [cuegui] Add OOM Increase field to Service Properties [#1160](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1160)
*   [cuegui] Open log files in binary mode for Python 3 comp [#1182](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1182)
*   [cuebot] Make frames and layers readonly after job is done [#1164](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1164)
*   Upgrade gRPC and protobuf dependencies. [#1185](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1185)
*   [rqd] Reduce the log level when failing to read a stat file. [#1191](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1191)
*   Update Dockerfile base images to fix compatibility issues. [#1198](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1198)
*   [pyoutline] Replace use of execfile() with exec(). [#1201](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1201)
*   [cuebot] Add a new property max_show_stale_days to control show expiration rule. [#1208](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1208)
*   [pycue] Add missing exception parsing to setAllocation. [#1172](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1172)
*   [rqd] On Windows, pass environment and properly escape command chars. [#1215](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1215)
*   [cuegui] Replace qApp with a new cuegui.App library. [#1193](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1193)
*   [cuebot] Automatically replace --log.frame-log-root with the new flag. [#1203](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1203)
*   [cuebot] Upgrade Log4j to 2.16. [#1080](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1080)