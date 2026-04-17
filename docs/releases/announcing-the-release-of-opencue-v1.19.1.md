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

- **Full Stack Sandbox Deployment**  
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

* c7a3cbb99587824975aad1ac11326364c5dd46c6 [docs] Update documentation version to 1.13.8 and add release notes (#2038)
* f96a852d4f13a59e00414c2eabb2e49b1be1dcdd [cuegui] Replace NodeGraphQtPy with NodeGraphQt (#2040)
* 55a90b3ee3f5470866f45b504a5a552b9d93ef5a [ci] Add Apache-2.0 license metadata to package pyproject.toml files and license check (#2039)
* 5a5738112704b6d18807bf13441e975dc704457e [cuegui] Fix AttributeError when assigning local cores from layers/frames (#2052)
* 1be2602636de5b6ecd5baa2b516a45d75b253cc3 [cuegui] Handle gRPC CANCELLED errors to fix UI refresh issues (#2042)
* cc83b7c5d70ccec0b83b7731447a4979e4191072 [cuegui] Fix LLU and Last Line columns not populating on large jobs (#2044)
* 97cf3e5a0f90271d95759407331aa2db51b60d02 [cuebot] Support multiple delimiters in filter action tag parsing (#2048)
* 747474ff97e7c837ee7725028b7dff6453c17fc7 [cuebot/cuegui/pycue/cueadmin] Add cue filter actions for UTIL and PRE layers (#2050)
* 942ef7054c1fca9e4e044673ead323a8952efef4 [docs] Add nav_order management utilities for documentation (#2055)
* f6018c996cb1ff9acd3d946b86077099e0123cc7 [rust/rqd] Trigger a kill_all_frames action when a host becomes nimby_locked (#2057)
* 5b2c8dab13aa9f5cd0b163e064153c2683e9aeee Update Slack channel link in README (#2059)
* 0bf7e2ceca432fba05f56628d911cb423d9ed318 [cuegui/docs] Fix EnableJobInteraction setting type handling (#2060)
* 21bc5498e7c069030c220e6b7876fa076eff4d87 [rust/rqd] Add OOM prevention logic with kill frame selection (#2064)
* 0e758f4f9881360cd29826b561e2a3d288f52bda [rust/rqd] Version Up rust/rqd (#2066)
* 34f4fd86615190012de33098e5fea4acc51fff99 [rust/rqd] Log OOM kill on rqd (#2067)
* 271e69a63fed06c2b53c4a6ced9fd7c5b65ab2cf [cuenimby] Add Enhanced CueNimby System Tray with OpenCue Icons, Emoji Status, and Connectivity Awareness (#2061)
* c879f4e9af507eb86490683afcfd98451c9757b7 [cuenimby] Fix working icon description in documentation (#2070)
* 016ea067f8fb0bad8978f6a674278d7e69dd977f Bump next-auth from 4.24.10 to 4.24.12 in /cueweb (#2068)
* 22c9cd9637d64cb8de06457cce3d06b0f41c66bf Fix PyOutline package name typo in installation docs (#2071)
* fe9610bf7f3b5db11a6ba9d41ab6c6670f7f35c0 [cuebot] Update Dockerfile to use openjdk:18-ea-18-slim-bullseye image (#2074)
* a5827b8164bf22e243b798cb389db54168264e1a [pycue] Remove six and unpin PyYaml (#2072)
* 1705100d69099cb3bd8c7a86e9dbb0669feb9d8c [cuebot] DB optional env vars to streamline custom deployment (#2076)
* 90d2d177b6a81c2f4f94afac308394c5f935fc3a [cuegui] Add error handling for gRPC connection failures in FrameMonitor (#2079)
* 648191df89ec4fd9c08c7dfeaf78af651b2028a1 Bump glob from 10.4.5 to 10.5.0 in /cueweb (#2080)
* b5959bb076523a840ceae276c54ad822308b7169 Bump js-yaml in /cueweb (#2081)
* b00240bc6ffd9313bd7d57acb9a9ac88bff8b80b [pyoutline] Layer module cleanup (#2073)
* 7a15bedaf52829750482675053f0def6c18da066 [Cuebot] Add booking show:facility exclusion list (#2087)
* 89ddcaf53a10b22a6ca95fa4c5eebc257d7d9512 [cuebot] Only replace username once on PostJobs (#2088)
* 5e374a88d5c6b9e09f1626673e3123f493191dc3 [rust/rqd] Add option to measure proc memory using PSS (#2089)
* fa916ffdd72266530359b7f2aa0d22e1e02acd8c [docs]  Move theme toggle (sun icon) into header (#2090)
* 8597e827c53f1fa57c2954a623f9417dfba085e7 [docs] Fix theme toggle not displaying due to duplicate const declara… (#2092)
* 084506c5437106215c273fe2e3b7c022ffc2de75 [rust/rqd] Fix memory bug on OOM killed frames (#2093)
* 6d381df9af250084932d47a75f4381c31e102b3c Bump jws from 3.2.2 to 3.2.3 in /cueweb (#2094)
* 64a133af2fedf4a7e78c843016cf73575f6e1222 [cueweb] Add CueWeb LDAP Authentication (#2096)
* dcf346c65437326bfe5cb286e11d773ddd8129a3 [cuegui] Fix CueJobMonitorTree not refreshing on property changes (#2100)
* c78ad9725f8442dccc13ef20d74961a6917a2108 [ci/cueweb/rest_gateway] Add Docker build jobs for cueweb and rest_gateway (#2098)
* 737282561eb86321dfc340f2cf371d133fc5df43 [ci/rust] Upgrade CI/CD macOS runners from macos-13 to macos-14 (#2099)
* e143627e156009fe57dc9b4b57a3ca2936f3e2ea [sandbox/docs/cueweb/rest_gateway] Add full stack sandbox deployment with CueWeb and REST Gateway (#2103)
* 9737ec56d92d4a5870307b84ae74313af81f9c46 Bump next from 14.2.32 to 14.2.35 in /cueweb (#2109)
* 74683bdba3db265b7c5b2ba6be692d690b23a5f4 [sandbox/rest_gateway] Fix Docker build compatibility for ARM64 and health checks (#2110)
* 5b8b02df6fb8371f975f0e30ff605b48c7390051 [cuebot/pycue/proto/sandbox/docs] Add full event-driven monitoring stack, enhance metrics, dashboards, and documentation (#2086)
* 515b701082b52d912bdca7573109f194e6715800 [rust/scheduler] Distributed Scheduler (#2104)
* 4f7e983f91269ab26f226616adbceae78ce8d203 [scheduler/docs] Add docs for the new scheduler module (#2113)
* 2d2ce13dc246e056a60364bfa7040a1d8783cede [rust] Add Copyright header on all rust files (#2114)
* 3599a1edc67a0c4a6e778395b0b100e83efb9c80 [cuegui] Fix ETA calculation type error and UTF-8 decoding in FrameMonitorTree (#2119)
* ce61412b723c4020a6676842e175a228b3026daa [cuegui] Fix layer tags validation to allow dashes and underscores (#2120)
* 8b39636198486380e34f7f394d83546907167a1c [RQD]\[FIX] Remove code duplication (#2123)
* b6633a30c605ca8b8d7b81462d4c6df1ae9e488e docs: add Docker setup for building documentation (#2130)
* 9d7fafcd7396300433aa985c92229401af69e578 [cueweb/docs] Update cueweb documentation with correct healthcheck using wget instead of curl (#2132)
* 081cbc18767936b3a0fe481fd93e34863abf9e89 Bump uri from 1.0.3 to 1.0.4 in /docs (#2135)
* 5519f7de32ee824aedcdcd9b4962c54652159cd6 [docs] Revert uri gem to 1.0.3 in Gemfile.lock (#2136)
* aba6471e76b6562ea9a151bf79fb8633450c1ec5 [docs] Remove obsolete version attribute from docker-compose.yml (#2137)
* ce6a8ff8af3198da104c38269104bcd4ab7f64e6 [RQD]\[FIX] Fix hyperthreading cores reservation (#2124)
* b81ba27dfad9d8f2776824aafe0a9810e00c44a5 [RQD]\[FIX] Skip os.chown for Windows (#2122)
* 624775ba966b267af00e0ca8c4bfd8566152dd30 [RQD]\[FIX] Windows log rotation retries (#2121)
* 2a27f490daf9872090be51ac5391ccfdca445528 [cuebot/cuegui/pycue/rqd] Store PSS and MaxPSS (#2112)
* 55e4c98ac50d3b2b3ec8bf4077a7cab13618c3b6 [rust] Enforce home version to stay compatible with rust 187 (#2145)
* 71ef9810a27fdb49fabcad2edac623f8e513fff8 [rqd/cicd] Only build rqd crate when packaging rqd binary (#2149)
* 8ec37c7be9b72c5e78fa815792b67f2ae325c1c0 [cuebot]\[FIX] Hardware tags update on Host restart (#2125)
* 01bd30d196e4fa05c8cd24db4ba2f2fa0a35dd8e [pycue] Fix service timeout LLU getter (#2146)
* c4b0cace267329a57c21de30e166c6a78651769f [cuegui/cuebot] Fix UI freeze on gRPC connection drops and add job unavailable notification (#2143)
* 453d6f4f407d8621c39dfa33e2a61ece38d20f75 [cuebot] Add scheduled subscription recalculation task (#2134)
* f926ca127bc0db8ade7b0d791376390505579569 [rqd] Fix race condition for ultrafast frames (#2157)
* 94f26f334d8f7deed2fef24db4585278847a801a [scheduler] Add job and layer envs to frame (#2161)
* b46e1704d0c833233fed459e51e7bbfb537a4af0 [scheduler] Fix datatype error on layer_dao (#2162)
* cafca69d89d27b8e5441091309aec403aa6766f8 [scheduler] Fix memory values on env vars (#2163)
* bda23e259ebb1ac8678c4a301c522316d5921978 [docker/ci/docs] Introduce unified Docker Compose stack with core-only defaults, monitoring, and quick start documentation (#2166)
* 0435d352c2cb75dad5e0916d1a4278bccd3d5d00 [cuebot] Add spring-boot-starter-mail into gradle dependencies (#2156)
* 9f333ca3c6d42db458b3fe6e6971b6f6fe00de69 [scheduler] Add hardware tags to rust scheduler (#2155)
* 777d05e0f63a16ed41300f6c20c5bf63bd7f48dd [docs] Add 2026 project update news and automate nav_order management (#2154)
* b8396bb18b84237623379b29952c8dafc4b87e07 [ci/docs] Fix permission denied error in docs pipeline (#2170)
* 57234a28e6931417342f121c7df916a9a4b1a990 [cuebot] Improve nimby retry logic (#2169)
* bad91914dadd637da02203014500de9336d1cd4f [ci/docs] Fix docs pipeline build failure and path references (#2171)
* 69ad038d31000f0a9bfd5801a10f900371598ce4 [cuegui] Add User Color sorting in Cuetopia job monitor (#2176)
* 35080d9488fca101aaf9cfd54b4a5a2638470e15 [docker] Remove prometheus exporter (#2179)
* a22f02472387c81a25d75141cedccc0e62e91dfb [Scheduler/Cuebot] Allow entire show migration to new scheduler (#2182)
* 0da9c5eab739b128a5e3860f976a8639b621c7b0 [rust/rqd] Fix process cache and timeout feature (#2160)
* 9a0db7a5c19252befded664022ecd38fc1a7ce1c [cuebot] Allow customizing the output_path for EmailSupport (#2153)
* 50c7a7acb3565d19721cd67e6e2958e68bbd5990 [scheduler] Improve scheduler metrics (#2178)
* e8d55d43e1f04f75913a75a006bea565aef21053 [Scheduler] Scope manual/hostname/hardware tag clusters to show and facility (#2188)
* f075786a8f10c85fafbc1d071ad4e59d0bdb7593 [docs] Fix broken www.opencue.io links to use docs.opencue.io (#2197)
* 66783c4368ea913d7ecac2c1eb83db4395c5c578 [cuegui] Make job-not-found popup notification configurable, default off (#2199)
* f6ecd97da42969a85d03db0e6a2d52cf4994d309 [scheduler] Fix race condition in multi-scheduler environments. (#2191)
* b9669ed7f4919b9e941f4727091acd4e69a34c08 [Cuebot] Fix stuck depend frames on transient failures (#2201)
* ec6fae9af73234c0bf96b9aea979e2c1394a54f2 [docs] Front page Design improvements (#2205)
* b5f90c1a58d429c470980b634dcf86fcb388b016 [docker] Update docker compose with newer versions and add profiles (#2175)
* bfd92f2ab274514af8457c83c7088dd049a6dd21 [docs/docker/ci] Remove redundant sandbox compose files and update to named Docker volumes (#2208)
* 5e58c02acd2954c51631178c892d50c5ce9569b0 [docs] Fix docs content spacing (#2210)
* 5928e2dd5bda0d57893325e7cef14faa934b0989 [rqd] Add CUE_HT env to hyperthreaded frames (#2207)
* 9cc2ef60d0a89d43fa2dc49a7d75b17e8bf881a5 [pyoutline] Allow adding or overriding outline modules via environment variable (#2193)
* 6078c547135af412dd3a815d51803ce5b93e3f41 [Cuebot] Remove unused threadpool properties (#2204)
* 42a48edbe3924375b5834b75065e4263938f18c4 [rqd] Fix available memory calculation error (#2211)
* 7e268fb3359e71d4b56eb97df9ac722322ea6ac5 [Cuebot] Fix possible race condition when updating host.int_mem_idle  (#2217)
* eb5ed41ca7531e2b144c374bf1670c42604d6bd1 [cuebot] Recover lost dependencies (#2219)
* 51392d985ea5b9132ef4a0bcd24b07aafd030888 [scheduler] Fix single-threaded bug (#2220)
* ea033f66093e3491ff0e794c50157f218a2b8faa [cuegui] fix max_cores bug (#2222)
* b1e1837cf56e6609e084f7d470fbd911ea16b21d [cuebot] VirtualProc allows cores above predefined max (#2223)
* 0d9b7cb90731e8f29bf037a99bad556f8c10585f [cuenimby] Make CueGUI launch command and menu label configurable (#2232)
* 609c9398fdbb363a3fd65edacadd6cc58c919814 [cuenimby] Fix config file open and notifications on headless render nodes (#2234)
* 42a17d95cb579fe076d721c85a3de2b33e63985f Update PULL_REQUEST_TEMPLATE.md (#2229)
* c08d809ed77b1e7910b8548e5f9bf467291570cb [docs] Add ai-policy to developer-guide docs (#2228)
* b263931150b63ef11ba6f24be3c94173b4a12353 [cuenimby] Fix CueNIMBY on headless Linux: editor, notifications, threading, frame info (#2237)
* 851d89b58f352d7045c08200f375096e8f45ee15 [scheduler] Fix memory_reserved divided by KIB instead of KB (#2241)
* 022f857b94a55284244f8f82362b8df9e114f3b0 [docs] Add comprehensive documentation for PyOutline and PyCuerun (#2212)
* 2ba7434d2448d949a1f00bf45bced8bc86fc7f9e [pyoutline/rqd] Add pycuerun entry point, fix CLI bugs, and improve sandbox support (#2215)
* 5e5914b957a129cc1020ace76672635ea839554e [rqd] Add windows support (#2165)
* ee9af694b29edab688209cc8e57bb3fb0bc67b30 [scheduler] Add sentry tracing (#2242)
* 487a92bb03112822f32f959ef761ea7353efe90b [rqd/cicd] Replace python/rqd by rust/rqd on docker stack (#2227)
* 0b850e3e3289b14f668852dd6bfa852f01faf131 [cuenimby] Load CueNIMBY default config from JSON file instead of hardcoding (#2244)
* f5fe0b1694be939f4a9e2c2242fda8f284a41f7e [pycue/cuegui] Add external facility feature (#2248)
* a94e6900bac7770a736c6f8302f496fd7defbb6f [cicd] Increase sonarqube memory (#2249)
* 8d306ace9b3d36255d82f8c4573b792cc8a0ea91 [scheduler] Allow jobs without an OS constraint to dispatch (#2246)
* a008061790f1dd1a1b36bb0f4c7f09424215434f [rqd] Add config option for default NIMBY lock at startup (#2247)
* 86b91648c856786fb7c7459996855a8d4859428a [scheduler/cuebot] Bulk resource accounting (#2198)
* cc5c2648a53d98bfc5cda80361dac6f80039d65a [scheduler] Add sqlx warnings as sentry events (#2250)