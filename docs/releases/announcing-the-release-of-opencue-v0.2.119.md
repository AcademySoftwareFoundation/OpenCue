---
layout: default
title: "v0.2.119 release"
parent: Releases
nav_order: 16
---

# Announcing the release of OpenCue v0.2.119

### OpenCue v0.2.119 release notes

#### Wednesday, October 16, 2019

---

[v0.2.119 of OpenCue](https://github.com/AcademySoftwareFoundation/OpenCue/releases/tag/0.2.119)
introduces a new *Limits* functionality that allows users to specify the
maximum number of concurrently running frames associated with that limit.
This change requires a full update of your OpenCue deployment and you must
run the database migrations to update an existing database. For more
information see
[OpenCue Limits functionality](https://lists.aswf.io/g/opencue-user/topic/opencue_limits_functionality/34376378).

To learn how to install and configure OpenCue, see [Getting started](/docs/getting-started/).

*   Added unit tests for `cuerqd.py` in
    [#490](https://github.com/AcademySoftwareFoundation/OpenCue/pull/490).
*   Made sure all CueGUI columns have valid sort functions in [#484](https://github.com/AcademySoftwareFoundation/OpenCue/pull/484).
*   Double clicking layer in CueGUI now filters the frames view in [#483](https://github.com/AcademySoftwareFoundation/OpenCue/pull/483).
*   Added a samples directory in
    [#471](https://github.com/AcademySoftwareFoundation/OpenCue/pull/471).
*   Left alignment no longer changes on selection in CueGUI in [#482](https://github.com/AcademySoftwareFoundation/OpenCue/pull/482).
*   Updated sandbox client packages install script in [#468](https://github.com/AcademySoftwareFoundation/OpenCue/pull/468).
*   Added unit tests for RqMachine in
    [#466](https://github.com/AcademySoftwareFoundation/OpenCue/pull/466).
*   Added basic limits functionality in
    [#414](https://github.com/AcademySoftwareFoundation/OpenCue/pull/414).
*   Fixed `createFrameByFrameDependency` grpc method in [#454](https://github.com/AcademySoftwareFoundation/OpenCue/pull/454).
*   Updated QThreads to shutdown on application close in [#450](https://github.com/AcademySoftwareFoundation/OpenCue/pull/450).
*   Removed unnecessary `exec_` that was causing crash in [#452](https://github.com/AcademySoftwareFoundation/OpenCue/pull/452).
*   Cleaned up wrapper methods so that no protobuf objects are passed or
    returned in
    [#449](https://github.com/AcademySoftwareFoundation/OpenCue/pull/449).
*   Fixed for `Layer.getFrames` in 
    [#447](https://github.com/AcademySoftwareFoundation/OpenCue/pull/447).
*   Added `FrameAttendantThread` unit tests in [#441](https://github.com/AcademySoftwareFoundation/OpenCue/pull/441).
*   Cleaned up the Enhancement template in [#443](https://github.com/AcademySoftwareFoundation/OpenCue/pull/443).
*   Added the `getChunk` method to FrameSet and substituted its result into
    commands in
    [#367](https://github.com/AcademySoftwareFoundation/OpenCue/pull/367).
*   Added more `RqCore` unit tests in
    [#439](https://github.com/AcademySoftwareFoundation/OpenCue/pull/439).
*   Fixed spelling of the `getRecentPgoutRate` method call in [#434](https://github.com/AcademySoftwareFoundation/OpenCue/pull/434).
*   Updated RQD lock and unlock behavior in [#435](https://github.com/AcademySoftwareFoundation/OpenCue/pull/435).
*   Updated Sandbox instructions and added a script to install client
    packages in
    [#432](https://github.com/AcademySoftwareFoundation/OpenCue/pull/432).
*   Fixed create new service bug in
    [#417](https://github.com/AcademySoftwareFoundation/OpenCue/pull/417).
*   Updated `setMinCores` to pass a percentage value where 100 = 1 core [#423](https://github.com/AcademySoftwareFoundation/OpenCue/pull/423).
*   Added a docker-compose sandbox environment in [#427](https://github.com/AcademySoftwareFoundation/OpenCue/pull/427).
*   Made sure log path is not empty when popping up log view [#415](https://github.com/AcademySoftwareFoundation/OpenCue/pull/415).
*   Added tests for `FrameMonitorTree` in
    [#412](https://github.com/AcademySoftwareFoundation/OpenCue/pull/412).
*   Added an initial round of RqCore tests in [#411](https://github.com/AcademySoftwareFoundation/OpenCue/pull/411).
*   Added more `MenuActions` tests in
    [#410](https://github.com/AcademySoftwareFoundation/OpenCue/pull/410).
*   Added tests for `JobActions` and `LayerActions` in [#407](https://github.com/AcademySoftwareFoundation/OpenCue/pull/407).
*   Updated to start bash before RQD to prevent zombie processes from being
    PID 1 in
    [#408](https://github.com/AcademySoftwareFoundation/OpenCue/pull/408).
*   Fixed find and get methods to raise `EntityNotFoundException` in PyCue [#406](https://github.com/AcademySoftwareFoundation/OpenCue/pull/406).
*   Wired up Python component test coverage in [#404](https://github.com/AcademySoftwareFoundation/OpenCue/pull/404).
*   Wired up Cuebot test coverage in
    [#403](https://github.com/AcademySoftwareFoundation/OpenCue/pull/403).
*   Added initial pipeline for SonarCloud scan in [#397](https://github.com/AcademySoftwareFoundation/OpenCue/pull/397).
*   Removed unnecessary conversion step when editing subscription size and
    burst size in
    [#400](https://github.com/AcademySoftwareFoundation/OpenCue/pull/400).
*   Added enums to appropriate wrappers in [#389](https://github.com/AcademySoftwareFoundation/OpenCue/pull/389).
*   Removed obsolete build/release script in [#388](https://github.com/AcademySoftwareFoundation/OpenCue/pull/388).
