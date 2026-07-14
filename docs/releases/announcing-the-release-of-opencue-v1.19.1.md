---
layout: default
title: "v1.19.1 release"
parent: Releases
nav_order: 0
---

# Announcing the release of OpenCue v1.19.1

## OpenCue v1.19.1 release notes

### April 13, 2026

---

To learn how to install and configure OpenCue, see our [Getting Started guide](https://docs.opencue.io/docs/quick-starts).

This release brings major new capabilities including a distributed scheduler written in Rust, comprehensive RQD improvements (OOM prevention, Windows support, PSS memory), CueWeb LDAP authentication, a full-stack sandbox deployment, and numerous bug fixes and stability improvements across the ecosystem.

## Major Features

- **Distributed Scheduler (Beta)**  
  Introduced a new distributed scheduler written in Rust, enabling scalable and high-performance job dispatching with support for hardware tags, show/facility-scoped clusters, environment variables, and Sentry tracing.  
  ([#2104](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2104)), ([#2113](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2113)), ([#2155](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2155)), ([#2182](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2182)), ([#2188](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2188)), ([#2198](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2198)), ([#2242](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2242))

- **Event-Driven Monitoring Stack**  
  Added a full event-driven monitoring stack with enhanced metrics, dashboards, and comprehensive documentation.  
  ([#2086](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2086))

- **CueWeb LDAP Authentication**  
  Added LDAP authentication support for CueWeb, enabling enterprise directory integration.  
  ([#2096](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2096))

- **Full-Stack Sandbox Deployment**  
  Introduced a unified Docker Compose sandbox deployment with CueWeb, REST Gateway, core-only defaults, monitoring profiles, and quick start documentation.  
  ([#2103](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2103)), ([#2110](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2110)), ([#2166](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2166))

- **RQD Windows Support (Release Candidate)**  
  Added full Windows support for RQD.  
  ([#2165](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2165)), ([#2121](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2121)), ([#2122](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2122))

- **Rust RQD OOM Prevention**  
  Added OOM prevention logic with intelligent frame kill selection and PSS memory measurement support in the Rust RQD implementation.  
  ([#2064](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2064)), ([#2067](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2067)), ([#2089](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2089)), ([#2093](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2093))

- **PSS Memory Measurement**  
  Added option to measure process memory using PSS (Proportional Set Size) and store PSS/MaxPSS values across Cuebot, CueGUI, PyCue, and RQD.  
  ([#2089](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2089)), ([#2112](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2112))

- **Booking Show:Facility Exclusion List**  
  Added the ability to configure booking exclusion lists per show and facility.  
  ([#2087](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2087))

- **External Facility Feature**  
  Added external facility support in PyCue and CueGUI.  
  ([#2248](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2248))

- **Filter Actions for UTIL and PRE Layers**  
  Added cue filter actions for UTIL and PRE layer types with support for multiple delimiters in filter action tag parsing.  
  ([#2050](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2050)), ([#2048](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2048))

## User Interface and Usability

- **CueGUI**  
  - Replaced NodeGraphQtPy with the upstream NodeGraphQt library  
    ([#2040](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2040))
  - Added User Color sorting in Cuetopia job monitor  
    ([#2176](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2176))
  - Fixed gRPC CANCELLED errors causing UI refresh failures  
    ([#2042](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2042)), ([#2079](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2079))
  - Fixed UI freeze on gRPC connection drops with job unavailable notification  
    ([#2143](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2143))
  - Fixed LLU and Last Line columns not populating on large jobs  
    ([#2044](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2044))
  - Fixed AttributeError when assigning local cores from layers/frames  
    ([#2052](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2052))
  - Fixed ETA calculation type error and UTF-8 decoding  
    ([#2119](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2119))
  - Fixed layer tags validation to allow dashes and underscores  
    ([#2120](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2120))
  - Fixed CueJobMonitorTree not refreshing on property changes  
    ([#2100](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2100))
  - Made job-not-found popup notification configurable, default off  
    ([#2199](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2199))
  - Fixed max_cores bug  
    ([#2222](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2222))
  - Added PSS and MaxPSS display support  
    ([#2112](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2112))

- **CueNIMBY**  
  - Enhanced system tray with OpenCue icons, emoji status, and connectivity awareness  
    ([#2061](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2061))
  - Made CueGUI launch command and menu label configurable  
    ([#2232](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2232))
  - Fixed operation on headless Linux render nodes (editor, notifications, threading)  
    ([#2237](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2237)), ([#2234](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2234))
  - Load default config from JSON file instead of hardcoding  
    ([#2244](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2244))

## Scheduler Improvements

- Distributed scheduler with show migration support  
  ([#2104](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2104)), ([#2182](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2182))
- Bulk resource accounting  
  ([#2198](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2198))
- Add job and layer environment variables to frames  
  ([#2161](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2161))
- Scope manual/hostname/hardware tag clusters to show and facility  
  ([#2188](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2188))
- Improved scheduler metrics  
  ([#2178](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2178))
- Allow jobs without an OS constraint to dispatch  
  ([#2246](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2246))
- Added Sentry tracing and sqlx warnings as Sentry events  
  ([#2242](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2242)), ([#2250](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2250))
- Fixed race condition in multi-scheduler environments  
  ([#2191](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2191))
- Fixed single-threaded bug, datatype errors, and memory value calculations  
  ([#2220](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2220)), ([#2162](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2162)), ([#2163](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2163)), ([#2241](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2241))

## RQD Improvements

- **Rust RQD:**  
  - Kill all frames when host becomes nimby_locked  
    ([#2057](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2057))
  - OOM prevention with kill frame selection and PSS memory measurement  
    ([#2064](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2064)), ([#2089](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2089))
  - Fixed memory bug on OOM killed frames and process cache/timeout  
    ([#2093](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2093)), ([#2160](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2160))
  - Replaced Python RQD with Rust RQD in Docker stack  
    ([#2227](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2227))

## Cuebot Improvements

- Added scheduled subscription recalculation task  
  ([#2134](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2134))
- Added spring-boot-starter-mail dependency  
  ([#2156](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2156))
- Allow customizing the output_path for EmailSupport  
  ([#2153](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2153))
- DB optional environment variables for custom deployments  
  ([#2076](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2076))
- VirtualProc allows cores above predefined max  
  ([#2223](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2223))
- Improved nimby retry logic  
  ([#2169](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2169))
- Updated Dockerfile to use openjdk:18-ea-18-slim-bullseye  
  ([#2074](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2074))
- Fixed stuck depend frames on transient failures  
  ([#2201](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2201))
- Fixed hardware tags update on host restart  
  ([#2125](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2125))
- Fixed race condition when updating host.int_mem_idle  
  ([#2217](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2217))
- Recover lost dependencies  
  ([#2219](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2219))
- Only replace username once on PostJobs  
  ([#2088](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2088))
- Removed unused threadpool properties  
  ([#2204](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2204))

## Documentation and Ecosystem

- **Documentation:**  
  - Added comprehensive documentation for the new scheduler module  
    ([#2113](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2113))
  - Added comprehensive documentation for PyOutline and PyCuerun  
    ([#2212](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2212))
  - Added AI policy to developer guide  
    ([#2228](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2228))
  - Added 2026 project update news  
    ([#2154](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2154))
  - Front page design improvements  
    ([#2205](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2205))
  - Fixed broken www.opencue.io links  
    ([#2197](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2197))
  - Added Docker setup for building documentation  
    ([#2130](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2130))
  - Updated CueWeb documentation with correct healthcheck using wget  
    ([#2132](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2132))
  - Added nav_order management utilities for documentation  
    ([#2055](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2055))

- **Docker and Deployment:**  
  - Unified Docker Compose stack with core-only defaults and monitoring profiles  
    ([#2166](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2166))
  - Updated docker compose with newer versions and profiles  
    ([#2175](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2175))
  - Removed redundant sandbox compose files, switched to named Docker volumes  
    ([#2208](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2208))
  - Replaced Python RQD with Rust RQD in Docker stack  
    ([#2227](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2227))

## Changes

- [docs] Update documentation version to 1.13.8 and add release notes [#2038](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2038)
- [cuegui] Replace NodeGraphQtPy with NodeGraphQt [#2040](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2040)
- [ci] Add Apache-2.0 license metadata to package pyproject.toml files and license check [#2039](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2039)
- [cuegui] Fix AttributeError when assigning local cores from layers/frames [#2052](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2052)
- [cuegui] Handle gRPC CANCELLED errors to fix UI refresh issues [#2042](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2042)
- [cuegui] Fix LLU and Last Line columns not populating on large jobs [#2044](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2044)
- [cuebot] Support multiple delimiters in filter action tag parsing [#2048](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2048)
- [cuebot/cuegui/pycue/cueadmin] Add cue filter actions for UTIL and PRE layers [#2050](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2050)
- [docs] Add nav_order management utilities for documentation [#2055](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2055)
- [rust/rqd] Trigger a kill_all_frames action when a host becomes nimby_locked [#2057](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2057)
- Update Slack channel link in README [#2059](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2059)
- [cuegui/docs] Fix EnableJobInteraction setting type handling [#2060](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2060)
- [rust/rqd] Add OOM prevention logic with kill frame selection [#2064](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2064)
- [rust/rqd] Version Up rust/rqd [#2066](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2066)
- [rust/rqd] Log OOM kill on rqd [#2067](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2067)
- [cuenimby] Add Enhanced CueNimby System Tray with OpenCue Icons, Emoji Status, and Connectivity Awareness [#2061](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2061)
- [cuenimby] Fix working icon description in documentation [#2070](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2070)
- Bump next-auth from 4.24.10 to 4.24.12 in /cueweb [#2068](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2068)
- Fix PyOutline package name typo in installation docs [#2071](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2071)
- [cuebot] Update Dockerfile to use openjdk:18-ea-18-slim-bullseye image [#2074](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2074)
- [pycue] Remove six and unpin PyYaml [#2072](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2072)
- [cuebot] DB optional env vars to streamline custom deployment [#2076](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2076)
- [cuegui] Add error handling for gRPC connection failures in FrameMonitor [#2079](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2079)
- Bump glob from 10.4.5 to 10.5.0 in /cueweb [#2080](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2080)
- Bump js-yaml in /cueweb [#2081](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2081)
- [pyoutline] Layer module cleanup [#2073](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2073)
- [Cuebot] Add booking show:facility exclusion list [#2087](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2087)
- [cuebot] Only replace username once on PostJobs [#2088](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2088)
- [rust/rqd] Add option to measure proc memory using PSS [#2089](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2089)
- [docs]  Move theme toggle (sun icon) into header [#2090](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2090)
- [docs] Fix theme toggle not displaying due to duplicate const declara… [#2092](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2092)
- [rust/rqd] Fix memory bug on OOM killed frames [#2093](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2093)
- Bump jws from 3.2.2 to 3.2.3 in /cueweb [#2094](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2094)
- [cueweb] Add CueWeb LDAP Authentication [#2096](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2096)
- [cuegui] Fix CueJobMonitorTree not refreshing on property changes [#2100](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2100)
- [ci/cueweb/rest_gateway] Add Docker build jobs for cueweb and rest_gateway [#2098](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2098)
- [ci/rust] Upgrade CI/CD macOS runners from macos-13 to macos-14 [#2099](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2099)
- [sandbox/docs/cueweb/rest_gateway] Add full-stack sandbox deployment with CueWeb and REST Gateway [#2103](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2103)
- Bump next from 14.2.32 to 14.2.35 in /cueweb [#2109](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2109)
- [sandbox/rest_gateway] Fix Docker build compatibility for ARM64 and health checks [#2110](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2110)
- [cuebot/pycue/proto/sandbox/docs] Add full event-driven monitoring stack, enhance metrics, dashboards, and documentation [#2086](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2086)
- [rust/scheduler] Distributed Scheduler [#2104](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2104)
- [scheduler/docs] Add docs for the new scheduler module [#2113](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2113)
- [rust] Add Copyright header on all rust files [#2114](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2114)
- [cuegui] Fix ETA calculation type error and UTF-8 decoding in FrameMonitorTree [#2119](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2119)
- [cuegui] Fix layer tags validation to allow dashes and underscores [#2120](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2120)
- [RQD]\[FIX] Remove code duplication [#2123](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2123)
- docs: add Docker setup for building documentation [#2130](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2130)
- [cueweb/docs] Update cueweb documentation with correct healthcheck using wget instead of curl [#2132](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2132)
- Bump uri from 1.0.3 to 1.0.4 in /docs [#2135](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2135)
- [docs] Revert uri gem to 1.0.3 in Gemfile.lock [#2136](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2136)
- [docs] Remove obsolete version attribute from docker-compose.yml [#2137](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2137)
- [RQD]\[FIX] Fix hyperthreading cores reservation [#2124](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2124)
- [RQD]\[FIX] Skip os.chown for Windows [#2122](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2122)
- [RQD]\[FIX] Windows log rotation retries [#2121](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2121)
- [cuebot/cuegui/pycue/rqd] Store PSS and MaxPSS [#2112](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2112)
- [rust] Enforce home version to stay compatible with rust 187 [#2145](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2145)
- [rqd/cicd] Only build rqd crate when packaging rqd binary [#2149](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2149)
- [cuebot]\[FIX] Hardware tags update on Host restart [#2125](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2125)
- [pycue] Fix service timeout LLU getter [#2146](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2146)
- [cuegui/cuebot] Fix UI freeze on gRPC connection drops and add job unavailable notification [#2143](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2143)
- [cuebot] Add scheduled subscription recalculation task [#2134](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2134)
- [rqd] Fix race condition for ultrafast frames [#2157](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2157)
- [scheduler] Add job and layer envs to frame [#2161](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2161)
- [scheduler] Fix datatype error on layer_dao [#2162](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2162)
- [scheduler] Fix memory values on env vars [#2163](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2163)
- [docker/ci/docs] Introduce unified Docker Compose stack with core-only defaults, monitoring, and quick start documentation [#2166](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2166)
- [cuebot] Add spring-boot-starter-mail into gradle dependencies [#2156](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2156)
- [scheduler] Add hardware tags to rust scheduler [#2155](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2155)
- [docs] Add 2026 project update news and automate nav_order management [#2154](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2154)
- [ci/docs] Fix permission denied error in docs pipeline [#2170](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2170)
- [cuebot] Improve nimby retry logic [#2169](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2169)
- [ci/docs] Fix docs pipeline build failure and path references [#2171](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2171)
- [cuegui] Add User Color sorting in Cuetopia job monitor [#2176](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2176)
- [docker] Remove prometheus exporter [#2179](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2179)
- [Scheduler/Cuebot] Allow entire show migration to new scheduler [#2182](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2182)
- [rust/rqd] Fix process cache and timeout feature [#2160](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2160)
- [cuebot] Allow customizing the output_path for EmailSupport [#2153](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2153)
- [scheduler] Improve scheduler metrics [#2178](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2178)
- [Scheduler] Scope manual/hostname/hardware tag clusters to show and facility [#2188](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2188)
- [docs] Fix broken www.opencue.io links to use docs.opencue.io [#2197](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2197)
- [cuegui] Make job-not-found popup notification configurable, default off [#2199](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2199)
- [scheduler] Fix race condition in multi-scheduler environments. [#2191](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2191)
- [Cuebot] Fix stuck depend frames on transient failures [#2201](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2201)
- [docs] Front page Design improvements [#2205](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2205)
- [docker] Update docker compose with newer versions and add profiles [#2175](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2175)
- [docs/docker/ci] Remove redundant sandbox compose files and update to named Docker volumes [#2208](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2208)
- [docs] Fix docs content spacing [#2210](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2210)
- [rqd] Add CUE_HT env to hyperthreaded frames [#2207](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2207)
- [pyoutline] Allow adding or overriding outline modules via environment variable [#2193](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2193)
- [Cuebot] Remove unused threadpool properties [#2204](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2204)
- [rqd] Fix available memory calculation error [#2211](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2211)
- [Cuebot] Fix possible race condition when updating host.int_mem_idle [#2217](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2217)
- [cuebot] Recover lost dependencies [#2219](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2219)
- [scheduler] Fix single-threaded bug [#2220](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2220)
- [cuegui] fix max_cores bug [#2222](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2222)
- [cuebot] VirtualProc allows cores above predefined max [#2223](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2223)
- [cuenimby] Make CueGUI launch command and menu label configurable [#2232](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2232)
- [cuenimby] Fix config file open and notifications on headless render nodes [#2234](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2234)
- Update PULL_REQUEST_TEMPLATE.md [#2229](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2229)
- [docs] Add ai-policy to developer-guide docs [#2228](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2228)
- [cuenimby] Fix CueNIMBY on headless Linux: editor, notifications, threading, frame info [#2237](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2237)
- [scheduler] Fix memory_reserved divided by KIB instead of KB [#2241](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2241)
- [docs] Add comprehensive documentation for PyOutline and PyCuerun [#2212](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2212)
- [pyoutline/rqd] Add pycuerun entry point, fix CLI bugs, and improve sandbox support [#2215](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2215)
- [rqd] Add windows support [#2165](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2165)
- [scheduler] Add sentry tracing [#2242](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2242)
- [rqd/cicd] Replace python/rqd by rust/rqd on docker stack [#2227](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2227)
- [cuenimby] Load CueNIMBY default config from JSON file instead of hardcoding [#2244](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2244)
- [pycue/cuegui] Add external facility feature [#2248](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2248)
- [cicd] Increase sonarqube memory [#2249](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2249)
- [scheduler] Allow jobs without an OS constraint to dispatch [#2246](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2246)
- [rqd] Add config option for default NIMBY lock at startup [#2247](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2247)
- [scheduler/cuebot] Bulk resource accounting [#2198](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2198)
- [scheduler] Add sqlx warnings as sentry events [#2250](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2250)