---
layout: default
title: "v0.15.22 release"
parent: Releases
nav_order: 5
---

# Announcing the release of OpenCue v0.15.22

### OpenCue v0.15.22 release notes

#### Saturday, April 2, 2022

---

[v0.15.22 of OpenCue](https://github.com/AcademySoftwareFoundation/OpenCue/releases/tag/v0.15.22)
includes the following changes and updates:

*   [rqd] Add automatic gRPC retries, retry grpc.StatusCode.UNAVAILABLE. [#1015](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1015)
*   Add GPU stats to allocation wrapper API. [#1016](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1016)
*   Fix number of GPU units in RunningFrameInfo. [#1017](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1017)
*   Make sure nestedJobWhiteboard is processed in order. [#973](https://github.com/AcademySoftwareFoundation/OpenCue/pull/973)
*   Remove unused stranded GPU code. [#1020](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1020)
*   Support GPU for Windows. [#1024](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1024)
*   [rqd] Add workaround for PowerShell Exitcode. [#1028](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1028)
*   [rqd] Remove extra space and extra MB from log output. [#1031](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1031)
*   [cuebot] Update GPU memory usage in the database from host report. [#1032](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1032)
*   [cuebot] Combine frame usage and memory usage updates. [#1006](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1006)
*   Lock protobuf to version 3.17.3 for Python 2. [#1046](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1046)
*   [rqd] Add usage of gRPC intercept_channel. [#1047](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1047)
*   [cuebot] Fix timeDiff for exception message. [#1049](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1049)
*   [pycue] Improve GPU API methods. [#1050](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1050)
*   [cuebot] Fix typos in GPU queries. [#1051](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1051)
*   Add CY2022 to testing pipeline. [#1048](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1048)
*   [cuebot] Fix GPU calculation in FrameCompleteHandler. [#1053](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1053)
*   [cuegui] Fix GPU field access in CueJobMonitorTree. [#1054](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1054)
*   [cuegui] Fix GPU editing and add scroll area to Layer Properties dialog. [#1055](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1055)
*   [cuebot] Avoid NullPointerException in SortableShow. [#1056](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1056)
*   [rqd] Replace isAlive with is_alive. [#1052](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1052)
*   Add FindLimit to pycue API [#1034](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1034)
*   [rqd] Fix use of hyperthreadingMultiplier. [#1013](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1013)
*   [rqd] Fix /proc/PID/stat parsing to support executable names with spaces and brackets. [#1029](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1029)
*   Use openjdk:11-jre-slim-buster [#1068](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1068)
*   Add thread pool properties [#1008](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1008)
*   Only restore jobIds added within last 3 days [#983](https://github.com/AcademySoftwareFoundation/OpenCue/pull/983)
*   Allow override max CPU cores and GPU units via Job spec [#1000](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1000)
*   Get RSS and %CPU for Windows [#1023](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1023)
*   Delete CORE_POINTS_RESERVED_MAX check logic [#1030](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1030)
*   [Cuebot][DB] Add history control [#1058](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1058)
*   [Cuebot] Add FIFO scheduling capability [#1060](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1060)
*   [Cuebot][SQL] Create limit index [#1057](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1057)
*   Changed psutil to 5.6.7 due to critical compilation error on Windows. [#1085](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1085)
*   [cuebot] Fix Group GPU APIs. [#1064](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1064)
*   Add Job.shutdownIfCompleted API method. [#1033](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1033)
*   [cuebot] Fix HostSearch substring for loose search. [#1076](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1076)
*   [cuegui] Optimize CueMonitorTree processUpdate API call. [#1077](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1077)
*   [cuebot] Switch to new version of embedded Postgres for unit tests. [#1087](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1087)
*   [cuebot] Introduce depend.satisfy_only_on_frame_success setting. [#1082](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1082)
*   Fix %CPU for Windows [#1090](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1090)
*   Standardize config env var and paths. [#1075](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1075)
*   [pyoutline] Standardize config env vars and paths. [#1074](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1074)
*   Replace DispatchQueue and BookingQueue with HealthyThreadPool [#1035](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1035)
*   Upgrade Flyway and fix Dockerfile. [#1110](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1110)
*   [cuegui] Split config code into a new module. [#1095](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1095)
*   Set smtp_host as env variable [#1119](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1119)