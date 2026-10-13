---
layout: default
title: "v1.34.22 release"
date: 2026-10-07
---

# Announcing the release of OpenCue v1.34.22

## OpenCue v1.34.22 release notes

### October 7, 2026

---

To learn how to install and configure OpenCue, see our [Getting Started guide](https://docs.opencue.io/docs/quick-starts).

This release introduces Maestro, a new scheduling solution built into Cuebot that replaces the standalone Rust scheduler. It also ships OpenCueWeb at full CueGUI and CueCommander parity, host-based limits with external license reporting, delayed layer starts, and a large set of fixes that harden Cuebot against frame double booking.

## Upgrade Notes

- **Database migrations V40 to V49.**  
  Cuebot applies them automatically at startup through Flyway. Back up your database before upgrading.

- **The standalone Rust scheduler has been removed.**  
  The distributed scheduler introduced as a beta in v1.19.1 is gone, and Maestro takes its place. The `show.b_scheduler_managed` flag is kept because Maestro's `managed` rollout mode uses it. Cuebot does not book shows that carry this flag. If you handed shows to the Rust scheduler, either enable Maestro's managed mode or clear the flag on every one of those shows with `cueadmin -scheduler-managed <show> off`. Otherwise they will stop booking.  
  ([#2533](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2533))

- **RQD `collect_pss` now defaults to off.**  
  On hosts with many processes, collecting PSS memory slowed RQD's report cycle enough to stall frame booking. Set `collect_pss: true` to turn it back on.  
  ([#2569](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2569))

- **OpenCueWeb and REST Gateway Docker images are not published yet.**  
  The Docker Hub repositories for these components are still being set up. Build the images from source for now (see the OpenCueWeb and REST Gateway deployment guides).  
  ([#2586](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2586))

## Major Features

- **Maestro, a new scheduling solution**  
  Maestro is a scheduler built into Cuebot that takes over dispatch per show. It adds host pinning, subscription fairness between shows, job priority, batched completion handling, and layer sizing from host reports and frame completions, with cold layers sized from their memory request. Its rollout mode lets you move shows over gradually. Maestro replaces the standalone Rust scheduler, which has been removed.  
  ([#2489](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2489)), ([#2533](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2533)), ([#2554](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2554)), ([#2557](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2557)), ([#2563](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2563)), ([#2574](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2574)), ([#2576](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2576)), ([#2577](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2577)), ([#2578](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2578)), ([#2583](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2583)), ([#2585](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2585))

- **OpenCueWeb: full CueGUI and CueCommander parity**  
  OpenCueWeb (formerly CueWeb) now covers the job, layer, and frame workflows of Cuetopia and the admin pages of CueCommander: hosts, shows, allocations, subscriptions, limits, services, stuck frames, redirect, and Monitor Cue. It also adds a CueSubmit job-submission UI, job dependency graphs, a plugin system, multi-facility routing, group-based authorization, an audit log, usage metrics, and an optional Loki backend for frame logs.  
  ([#2353](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2353)), ([#2373](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2373)), ([#2377](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2377)), ([#2421](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2421)), ([#2423](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2423)), ([#2426](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2426)), ([#2433](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2433)), ([#2448](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2448)), ([#2461](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2461)), ([#2484](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2484))

- **Host-based limits with external license reporting**  
  Limits can now count per host, and an external reporter can feed in license usage, so frames only book when a license is available. Job specs that reference undefined limits are now rejected at submission.  
  ([#2520](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2520)), ([#2514](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2514))

- **Delayed layer start**  
  A layer can carry a start-after time, and Cuebot won't book its frames before then. Operators can set it from CueGUI, pycue (`Layer.setStartAfter()`), or OpenCueWeb. Cuebot can also push it back automatically when a frame exits with a configured status, such as a license shortage detected by RQD's log-based exit-status rules, so frames retry later without using up retries.  
  ([#2502](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2502)), ([#2507](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2507))

- **Restart RQD service with frame recovery**  
  New CueGUI and OpenCueWeb host actions restart the RQD service, either right away or once the host has drained and gone idle. The machine itself is never rebooted. Running frames survive an immediate restart and the new RQD picks them back up.  
  ([#2529](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2529))

- **Frame double-booking prevention**  
  Cuebot no longer frees and rebooks a frame unless it has confirmed the previous run is dead. This covers lost procs, unreachable hosts, and frame launches whose outcome is unknown.  
  ([#2441](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2441)), ([#2471](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2471)), ([#2506](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2506)), ([#2508](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2508)), ([#2510](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2510))

- **Slow RQD hosts no longer stall booking**  
  Frame launches are confirmed asynchronously, and a per-host breaker stops a slow or unresponsive host from holding up the booking threads.  
  ([#2567](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2567)), ([#2568](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2568)), ([#2569](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2569))

## User Interface and Usability

- **CueGUI**  
  - Added a "Take Ownership" action for hosts owned by another user ([#2340](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2340))
  - Added a "Shutdown If Completed" job action ([#2523](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2523))
  - Added layer dispatch order control ([#2354](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2354))
  - Added search and scrolling to the frame monitor Filter Layers menu ([#2482](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2482))
  - Show /mcp percent free in Monitor Hosts, split the "Temp Free" column, and fixed temp bar overflow on stale hosts ([#2263](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2263)), ([#2313](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2313))
  - Faster CueMonitorTree refreshes ([#2370](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2370))
  - Fixed preview-frame errors and crashes ([#2389](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2389)), ([#2395](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2395))
  - Fixed blank Stuck Frame and Redirect pages when the default show is missing ([#2443](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2443)), ([#2445](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2445))

- **API additions**  
  - `eligibleTime()` on Job, Layer, and Frame; `submissionTime()` on Frame; `startTime()` and `stopTime()` on Layer ([#2325](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2325)), ([#2337](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2337)), ([#2338](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2338))
  - Department wrapper in pycue ([#2427](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2427))

- **CueAdmin**  
  - Lock-state filter and idle sort for the host list ([#2480](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2480))
  - Fixed `-create-sub` failing with "'str' object is not callable" ([#2261](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2261))

## RQD Improvements

- Exit status can be overridden based on rules matched against the frame log ([#2501](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2501))
- FrameCompleteReports are retried until Cuebot accepts them ([#2473](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2473)), ([#2504](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2504))
- Config overrides for cores, procs, memory size, and hostname ([#2257](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2257))
- Stats from co-tenant frames are listed in the log footer ([#2497](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2497))
- Fixed recovery mode, SIGKILL masking, and temp storage reporting when temp_path is a symlink ([#2503](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2503)), ([#2312](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2312)), ([#2265](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2265))

## Cuebot Improvements

- Shutdown now drains thread pools before closing the data source ([#2271](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2271)), ([#2273](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2273))
- Faster `fix_stuck_depend_counts` query and dependency cleanup indexes ([#2272](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2272))
- Fixed dispatching when only one show is active ([#2327](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2327))
- Satisfying a dependency now respects the depend config ([#2352](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2352))
- Fixed `getWhatDependsOn(Frame)` and gRPC channel closing ([#2278](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2278)), ([#2274](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2274))
- Added a stranded-cores memory metric ([#2394](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2394))

## Documentation and Ecosystem

- **REST Gateway:** Swagger UI and OpenAPI spec generation, and a gRPC receive limit raised above 4 MB ([#2511](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2511)), ([#2466](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2466))
- **PyOutline:** configuration options can be overridden with environment variables ([#2556](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2556))
- **Governance and security:** added the ASWF governance document and updated the CRA security policy ([#2436](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2436)), ([#2528](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2528))
- **Docs:** reworked documentation navigation ([#2521](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2521))

## Changes

- [scheduler] Fix bug on limits query [#2253](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2253)
- [scheduler] Fix bug on recompute job resources logic [#2254](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2254)
- [rqd] Add override cores, procs, memory_size and hostname [#2257](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2257)
- [scheduler] Fix regression with layers containing multiple tags [#2258](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2258)
- [rest_gateway] Bump Go base image to 1.25 to fix Docker build [#2259](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2259)
- [docs] Update documentation version to 1.19.1 and add release notes [#2255](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2255)
- [cueadmin] Fix -create-sub failing with "'str' object is not callable" [#2261](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2261)
- [cuegui] Show /mcp percent free in Monitor Hosts [#2263](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2263)
- [rust-rqd] Report correct temp storage when temp_path is a symlink [#2265](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2265)
- [cuebot] Optimize fix_stuck_depend_counts query [#2272](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2272)
- [cuebot] Rework shutdown logic to allow draining threadpools [#2271](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2271)
- [cuebot] Ensure cueDataSource is not killed before queues [#2273](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2273)
- [cuebot] Fix issue on getWhatDependsOn(Frame) [#2278](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2278)
- [cuebot] Reformat DaoJdbc files [#2297](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2297)
- [cuegui] Fix Temp bar overflow on stale hosts and split "Temp Free" column in two [#2313](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2313)
- [cuegui] Update tooltip to clarify percentage-based display and behavior [#2316](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2316)
- [CICD] Cache Rust deps and add timeouts to rust-pipeline [#2321](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2321)
- [rqd] Fix sigkill masking bug [#2312](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2312)
- [cuebot] Fix channel closing issue [#2274](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2274)
- [cuebot/proto/pycue/cuegui/docs] Add eligibleTime() to Job, Layer, and Frame [#2325](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2325)
- [CI/CD] Fix Test Documentation Build: use `python -m pip` in build_sphinx_docs.sh [#2334](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2334)
- [cueweb] Bump Next.js to 15.5.18 to patch CVE-2026-44578 (WebSocket SSRF) [#2332](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2332)
- [cueweb] Add per-job subscribe bell for completion notifications [#2335](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2335)
- [cuegui/pycue] Add "Take Ownership" action for hosts already owned by another user [#2340](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2340)
- [cueweb] Add human-readable age column with smart formatting [#2336](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2336)
- Bump faraday from 2.13.4 to 2.14.2 in /docs [#2342](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2342)
- [cueweb] Add job progress tooltip [#2331](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2331)
- [cueweb] Add frame state filter chips [#2330](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2330)
- [cuebot] Fix bug preventing dispatching with a single active show [#2327](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2327)
- [cuegui] Fix stray blue line over layer Name column on macOS [#2343](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2343)
- [cueweb] Fix all high and critical npm vulnerabilities [#2346](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2346)
- [cueweb/docs] Document per-job completion notifications [#2348](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2348)
- [cueweb/docs] Add job comments panel with CRUD and predefined macros [#2349](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2349)
- [cueweb] Add Apache 2.0 license header to CueWeb source files [#2350](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2350)
- [cuebot/proto/pycue/cuegui/docs] Add submissionTime() to Frame [#2337](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2337)
- [cuebot] Make Satisfy depend adhere to depend config [#2352](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2352)
- [cueweb] Use toast for job-finished notifications and harden poller [#2341](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2341)
- [scheduler] Handle threadable frames similar to cuebot [#2328](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2328)
- [cuebot/proto/pycue/cuegui/docs] Add startTime() and stopTime() to Layer [#2338](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2338)
- [cuegui/cuebot] Optimize CueMonitorTree [#2370](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2370)
- [cuegui] Fix QT's thread-affinity warning [#2371](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2371)
- [cuegui] Revert a portion of #2370 [#2378](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2378)
- [cueweb/docs/sandbox/images] Complete Professional UI/UX Foundations milestone: CueGUI parity, monitoring UX overhaul, responsive/mobile support, and major CueWeb usability improvements [#2353](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2353)
- [cueweb/docs] Add CueSubmit job-submission UI (CueSubmit CLI parity + improvements) [#2373](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2373)
- [cueweb/docs] Job menu actions: Part 1 - Unmonitor, View Job Details, Copy Job Name, Comments, Pause, Unpause, Auto-Eat On and Off, Retry Dead Frames, Eat Dead Frames, Kill Job. Part 2 - Email artist, Request Cores, Subscribe to Job, Set Priority [#2374](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2374)
- [cueweb/docs] Job menu actions: Part 3 -  Implement Dependencies (View Dependencies, Dependency Wizard, Drop External / Internal Dependencies) on CueWeb > Cuetopia job menu + Tree view [#2386](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2386)
- [cuegui] Fix preview frames error [#2389](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2389)
- [cueweb] Add job dependency graph: inline panel + Cuetopia toggle [#2377](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2377)
- [cueweb/docs] Document the job dependency graph (inline panel + Cuetopia View Job Graph toggle) [#2392](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2392)
- [scheduler] Resource accounting on Redis [#2323](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2323)
- [cuegui] Fix crash when closing preview dialog before images are ready [#2395](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2395)
- [cuebot] Add memory stranded cores metric [#2394](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2394)
- [cueweb/docs] Host and Allocation Management: Hosts monitor page - Initial version [#2391](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2391)
- [cueweb/docs] Host management actions: lock/unlock, reboot, detail page, tag editor [#2397](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2397)
- [scheduler] Make b_scheduler_managed the single source of truth [#2401](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2401)
- [rqd] Improve logging on fs and caps errors [#2402](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2402)
- [cuebot] Release procs on frame-complete for scheduler-managed shows [#2403](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2403)
- [cueweb] Add Create Show modal [#2376](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2376)
- [cueweb/docs] Add Shows page: stats table, Show Properties, subscriptions (CueCommander parity) [#2406](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2406)
- [cuebot] Complete the gRPC response in ShowInterface.SetCommentEmail [#2409](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2409)
- [cueweb/docs] Add Allocations page (CueCommander parity) [#2410](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2410)
- [cueweb] Job Management actions: min/max cores, batch confirmation, unbook (#2281, #2283, #2288) [#2405](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2405)
- [cueweb] Add per-show group tree with drag-to-reparent [#2404](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2404)
- [scheduler] Add scheduling mode: E-PVM [#2398](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2398)
- [scheduler] Optimization pass [#2411](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2411)
- Add ASWF Governance document [#2436](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2436)
- [cueweb/docs] Add Limits page (CueCommander parity) [#2412](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2412)
- [cueweb/docs] Add Subscriptions page and Subscriptions Graph page (CueCommander parity) [#2413](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2413)
- [cueweb/docs] Add Services (Facility Service Defaults) page (CueCommander parity) [#2415](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2415)
- [cueweb/docs] Add Stuck Frames page (CueCommander parity) [#2416](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2416)
- [cueweb/docs] Add Redirect page (CueCommander parity) [#2418](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2418)
- [cuebot] Fix Silent frame double booking [#2441](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2441)
- [cuegui] Fix blank Stuck Frame page when default show is missing [#2445](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2445)
- [cuegui] Fix blank Redirect page when default show is missing [#2443](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2443)
- [cueweb/docs] Add Cuebot Facility switching (server-side gateway routing) [#2433](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2433)
- [cueweb/docs] Add "About CueWeb" dialog and version sourcing from VERSION.in [#2442](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2442)
- [cueweb] Add optional group-based authorization gate [#2431](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2431)
- [cueweb/docs] Add plugin system: loader, settings, menu selection, and samples [#2448](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2448)
- [cueweb/docs] Add view presets, immersive mode, and split-view workspaces [#2449](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2449)
- [cueweb/docs] Add optional Loki backend for frame log viewing [#2447](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2447)
- [cueweb/docs] Add per-facility connection health and runtime facility config [#2439](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2439)
- [cueweb/docs] Monitor Hosts: Full CueCommander parity [#2421](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2421)
- Bump form-data from 4.0.5 to 4.0.6 in /cueweb [#2450](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2450)
- Bump @babel/core from 7.25.2 to 7.29.6 in /cueweb [#2451](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2451)
- Bump concurrent-ruby from 1.3.5 to 1.3.7 in /docs [#2452](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2452)
- Bump faraday from 2.14.2 to 2.14.3 in /docs [#2453](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2453)
- [cueweb/docs] Job/Layer/Frame context-menu parity + frame log viewer enhancements [#2426](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2426)
- [cueweb/docs] Add Monitor Cue page (CueCommander parity) [#2423](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2423)
- [cueweb/docs] Job graph: show layers, right-click layer menu, double-click to open [#2457](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2457)
- [cueweb/docs] Add per-user usage metrics (Prometheus) + Grafana dashboard [#2459](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2459)
- [cueweb/docs] Add CueWeb Audit web action audit system [#2461](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2461)
- [cuebot/cuegui] Feature add layer dispatchorder control [#2354](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2354)
- [scheduler] Add end-to-end stress tests to scheduler [#2464](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2464)
- [scheduler] Avoid starvation [#2463](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2463)
- [scheduler] Gate cluster feed on an awake-set scan [#2465](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2465)
- [rest_gateway] Raise REST gateway gRPC max receive message size above 4MB default [#2466](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2466)
- [cueweb] Gate full CueCommander and CueSubmit behind admin authorization [#2468](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2468)
- [cuebot] Defer release proc when host non-accessible [#2471](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2471)
- [cueweb] Fix Monitor Cue job row height to match show/group rows [#2470](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2470)
- [cueweb] Request Okta groups scope for group memberships [#2475](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2475)
- [cueadmin/docs] Add lock-state filter and idle sort to host list [#2480](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2480)
- [cuegui/docs] Add search and scrolling to frame monitor Filter Layers menu [#2482](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2482)
- [scheduler/cuebot] Replace Redis-backed accounting with in-memory store + PG LISTEN/NOTIFY [#2472](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2472)
- Bump ws from 8.20.1 to 8.21.1 in /cueweb [#2485](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2485)
- [pycue/cuegui/cuebot] Add Department wrapper and fix TasksDialog (#2399) [#2427](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2427)
- [cueweb/docs] Add CueWeb full-release news post and refresh news nav_order [#2479](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2479)
- [cueweb/docs] Rename CueWeb to OpenCueWeb across documentation [#2484](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2484)
- Bump next-auth from 4.24.14 to 4.24.15 in /cueweb [#2492](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2492)
- Bump fast-uri from 3.1.2 to 3.1.4 in /cueweb [#2491](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2491)
- Bump postcss from 8.5.14 to 8.5.18 in /cueweb [#2493](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2493)
- Bump next from 15.5.18 to 15.5.22 in /cueweb [#2494](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2494)
- [rqd] List co-tenant frame's stats on log footer [#2497](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2497)
- [rqd] Frame log based exit status override [#2501](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2501)
- [rqd/cuebot] Add a retry mechanism for FrameCompleteReport [#2473](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2473)
- [rqd] Improve FrameCompleteReport delivery logic [#2504](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2504)
- [cuebot/cuegui/pycue/rqd] Allow delaying a layer start [#2502](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2502)
- [cuebot] Add extra measures to prevent double booking [#2506](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2506)
- [cuebot] Prevent Lost procs from being deferred forever [#2508](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2508)
- Bump brace-expansion in /cueweb [#2496](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2496)
- Bump postcss and next in /cueweb [#2499](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2499)
- Bump fast-uri from 3.1.4 to 3.1.5 in /cueweb [#2500](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2500)
- [cueweb/docs] Allow delaying a layer start [#2507](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2507)
- [cuebot] Fail closed on frame launches with unknown outcome [#2510](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2510)
- [rest_gateway/docs] Add Swagger UI and OpenAPI spec generation [#2511](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2511)
- Bump fast-uri from 3.1.5 to 3.1.7 in /cueweb [#2518](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2518)
- Bump postcss-selector-parser from 6.1.2 to 6.1.4 in /cueweb [#2516](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2516)
- [pyoutline] Override configuration options with environment variables. [#2517](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2517)
- [pyoutline] Fix reStructuredText error in read_config_from_disk docstring [#2522](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2522)
- Bump browserslist from 4.28.2 to 4.28.8 in /cueweb [#2519](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2519)
- [cuebot/proto/pycue/cuegui] Add host-based limits with external license reporting [#2520](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2520)
- [cuegui] Add "Shutdown If Completed" job action [#2523](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2523)
- [cuebot] Reject job specs referencing undefined limits [#2514](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2514)
- [cuebot] Replace EOL bullseye base image to unbreak CI [#2527](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2527)
- [rqd] Fix rqd recovery mode [#2503](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2503)
- Bump js-yaml in /cueweb [#2524](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2524)
- Bump sharp from 0.35.3 to 0.35.4 in /cueweb [#2525](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2525)
- Bump next from 16.3.0 to 16.3.4 in /cueweb [#2526](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2526)
- [doc] Fix documentation nav hack [#2521](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2521)
- \[FIX\][pyoutline] Compact frame range layer [#2509](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2509)
- [rqd/cuebot] Add restart-RQD-service host actions with frame recovery [#2529](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2529)
- [all] Maestro, a new scheduling solution [#2489](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2489)
- [security] Update security CRA [#2528](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2528)
- [all] Remove the standalone Rust scheduler [#2533](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2533)
- Fix Rust RQD docs: wrong Docker build context and broken /OpenCue/docs/ links [#2535](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2535)
- [cuebot/maestro] Host pinning and improvements [#2554](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2554)
- Redo of #2517 [#2556](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2556)
- [ci/cueweb/rest_gateway] Publish CueWeb and REST Gateway Docker images [#2558](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2558)
- [Maestro]: completion-forward relay for the isolated-leader rollout [#2557](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2557)
- Bump fast-uri from 3.1.5 to 3.1.8 in /cueweb [#2532](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2532)
- Bump nanoid from 3.3.17 to 3.3.19 in /cueweb [#2534](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2534)
- [cuebot/maestro] Keep legacy booking off scheduler-managed shows [#2563](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2563)
- [cuebot/rqd] Stop slow RQD hosts from stalling frame booking [#2567](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2567)
- [cuebot] Default the launch breaker properties in the Spring context [#2568](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2568)
- [rqd] Default collect_pss to off [#2569](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2569)
- [rest-gateway] Bump Go base image to 1.27 for rest_gateway [#2572](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2572)
- [Maestro] Subscription fairness between shows [#2574](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2574)
- [build] Support forcing patch version when building packages [#2571](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2571)
- Maestro priority [#2576](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2576)
- Maestro: drain completions twenty at a time [#2577](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2577)
- Maestro: size a layer from reports and completions [#2578](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2578)
- [cuebot] Maestro: persist layer memory raises to the database [#2583](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2583)
- [cuebot] Maestro: size cold layers' cores from their memory ask [#2585](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2585)
- [ci] Don't fail pipelines on missing rest-gateway/cueweb Docker Hub repos [#2586](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2586)
- [docs] Update documentation version to 1.34.20 and add release notes [#2597](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2597)
- [ci] Resolve release tags to master in the version scripts [#2598](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2598)
