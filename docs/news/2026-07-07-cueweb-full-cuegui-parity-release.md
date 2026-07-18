---
layout: default
title: "July 7, 2026: Announcing OpenCueWeb: The Complete Web-Based OpenCue GUI"
parent: News
nav_order: 0
---

# Announcing OpenCueWeb: The Complete Web-Based OpenCue GUI

### First Full Release: OpenCueWeb Now Replicates All of CueGUI (Cuetopia and CueCommander)

#### July 7, 2026

---

We're excited to announce that **OpenCueWeb**, the browser-based OpenCue GUI, is now **feature-complete and merged to the [OpenCue master branch](https://github.com/AcademySoftwareFoundation/OpenCue)**. OpenCueWeb replicates the complete functionality of **CueGUI**, covering both **Cuetopia** (job, layer, and frame monitoring and management) and **CueCommander** (host, allocation, show, subscription, service, limit, and facility administration), all in the browser with no desktop install required.

![OpenCueWeb dashboard](/assets/images/cueweb/cueweb_dashboard.png)

## Why OpenCueWeb

CueGUI is a desktop application, but it requires a local install, a graphical environment, and network access to Cuebot. OpenCueWeb removes that friction: artists and administrators can now monitor and manage the render farm from any modern browser, on any platform, behind standard web authentication. This makes OpenCue easier to access for remote workers, easier to deploy for studios, and easier to integrate into existing web-based pipelines.

## Cuetopia Parity

OpenCueWeb now provides the full set of Cuetopia job-management capabilities:

- **Job menu actions**: pause / unpause, retry dead frames, eat dead frames, kill, unbook, request cores, set priority, subscribe to job, email artist, and job comments.
- **Min/max cores** dialog and batch confirmation for multi-job actions.
- **Job dependency graph** with an inline panel, a Cuetopia toggle, and a dependency wizard (view dependencies, drop external / internal dependencies).
- **CueSubmit in the browser**: a job-submission UI that brings CueSubmit-equivalent functionality to the web.
- **Frame and layer management**: layer property editing, frame state filter chips, human-readable age columns, per-state progress bars, and an enhanced frame log viewer.

![OpenCueWeb Monitor Jobs](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_mainpage.png)

Clicking a job reveals its layers and frames inline:

![OpenCueWeb inline layers and frames](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_layersframes.png)

The job dependency graph renders below the layers and frames:

![OpenCueWeb job dependency graph](/assets/images/cueweb/cueweb_cuetopia_view_job_graph_monitor_jobs_dependency_graph_only.png)

## CueCommander Parity

The administrative side of CueGUI is fully represented as well:

- **Monitor Hosts** with full CueCommander parity, plus host actions: lock / unlock, reboot, tag editing, and host detail pages.
- **Monitor Cue** page.
- **Shows** page with a stats table, Show Properties, and subscriptions, plus a Create Show modal and per-show group tree with drag-to-reparent.
- **Subscriptions** and **Subscriptions Graph** pages.
- **Services** (Facility Service Defaults), **Limits**, and **Allocations** pages.
- **Stuck Frames** and **Redirect** pages.

![OpenCueWeb CueCommander Monitor Hosts](/assets/images/cueweb/cueweb_cuecommander_monitor_hosts.png)

The Shows page with stats, Show Properties, and subscriptions:

![OpenCueWeb CueCommander Shows](/assets/images/cueweb/cueweb_cuecommander_shows.png)

Allocations and Limits pages:

![OpenCueWeb CueCommander Allocations](/assets/images/cueweb/cueweb_cuecommander_allocation.png)

![OpenCueWeb CueCommander Limits](/assets/images/cueweb/cueweb_cuecommander_limits.png)

## Platform Features

Beyond CueGUI parity, OpenCueWeb adds capabilities that a modern web application enables:

- **Cuebot facility switching** with server-side gateway routing and per-facility connection health.
- **Authorization**: an optional group-based authorization gate, admin gating for the full CueCommander and CueSubmit, and Okta group memberships.
- **Extensibility**: a plugin system with a loader, settings, menu selection, and sample plugins.
- **Observability**: per-user usage metrics (Prometheus) with a Grafana dashboard, and an OpenCueWeb audit trail that tracks who did what, when, and with what outcome.
- **Workflow**: view presets, immersive mode, and split-view workspaces.
- **Logs**: an optional Loki backend for frame log viewing.

Switch the active Cuebot facility from the menu, with per-facility health indicators:

![OpenCueWeb Cuebot facility menu](/assets/images/cueweb/cueweb_cuebot_facility_menu.png)

The OpenCueWeb audit trail tracks who did what, when, and with what outcome:

![OpenCueWeb audit trail](/assets/images/cueweb/cueweb_admin_cueweb_audit.png)

## Contributors

OpenCueWeb reached full parity through sustained work, with a burst of collaboration during DevDays 2026:

- [Ramon Figueiredo](https://github.com/ramonfigueiredo): 43 commits, including most of the OpenCueWeb code and all of the OpenCueWeb and REST Gateway documentation. [Full list of PRs](https://github.com/AcademySoftwareFoundation/OpenCue/pulls?q=is%3Apr+is%3Aclosed+label%3Acueweb+author%3Aramonfigueiredo)
  - [#2470](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2470): [cueweb] Fix Monitor Cue job row height to match show/group rows
  - [#2468](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2468): [cueweb] Gate full CueCommander and CueSubmit behind admin authorization
  - [#2466](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2466): [rest_gateway] Raise REST gateway gRPC max receive message size above 4MB default
  - [#2461](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2461): [cueweb/docs] Add CueWeb Audit web action audit system
  - [#2459](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2459): [cueweb/docs] Add per-user usage metrics (Prometheus) + Grafana dashboard
  - [#2457](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2457): [cueweb/docs] Job graph: show layers, right-click layer menu, double-click to open
  - [#2449](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2449): [cueweb/docs] Add view presets, immersive mode, and split-view workspaces
  - [#2448](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2448): [cueweb/docs] Add plugin system: loader, settings, menu selection, and samples
  - [#2447](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2447): [cueweb/docs] Add optional Loki backend for frame log viewing
  - [#2442](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2442): [cueweb/docs] Add "About CueWeb" dialog and version sourcing from VERSION.in
  - [#2439](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2439): [cueweb/docs] Add per-facility connection health and runtime facility config
  - [#2433](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2433): [cueweb/docs] Add Cuebot Facility switching (server-side gateway routing)
  - [#2431](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2431): [cueweb] Add optional group-based authorization gate
  - [#2426](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2426): [cueweb/docs] Job/Layer/Frame context-menu parity + frame log viewer enhancements
  - [#2423](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2423): [cueweb/docs] Add Monitor Cue page (CueCommander parity)
  - [#2421](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2421): [cueweb/docs] Monitor Hosts: Full CueCommander parity
  - [#2418](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2418): [cueweb/docs] Add Redirect page (CueCommander parity)
  - [#2416](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2416): [cueweb/docs] Add Stuck Frames page (CueCommander parity)
  - [#2415](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2415): [cueweb/docs] Add Services (Facility Service Defaults) page (CueCommander parity)
  - [#2413](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2413): [cueweb/docs] Add Subscriptions page and Subscriptions Graph page (CueCommander parity)
  - [#2412](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2412): [cueweb/docs] Add Limits page (CueCommander parity)
  - [#2410](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2410): [cueweb/docs] Add Allocations page (CueCommander parity)
  - [#2409](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2409): [cuebot] Complete the gRPC response in ShowInterface.SetCommentEmail
  - [#2406](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2406): [cueweb/docs] Add Shows page: stats table, Show Properties, subscriptions (CueCommander parity)
  - [#2397](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2397): [cueweb/docs] Host management actions: lock/unlock, reboot, detail page, tag editor
  - [#2392](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2392): [cueweb/docs] Document the job dependency graph (inline panel + Cuetopia View Job Graph toggle)
  - [#2386](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2386): [cueweb/docs] Job menu actions Part 3: Dependencies (View Dependencies, Dependency Wizard, Drop External / Internal Dependencies)
  - [#2374](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2374): [cueweb/docs] Job menu actions Part 1 & 2: Unmonitor, View Job Details, Copy Job Name, Comments, Pause/Unpause, Auto-Eat, Retry/Eat Dead Frames, Kill, Email Artist, Request Cores, Subscribe to Job, Set Priority
  - [#2373](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2373): [cueweb/docs] Add CueSubmit job-submission UI (CueSubmit CLI parity + improvements)
  - [#2353](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2353): [cueweb/docs/sandbox/images] Complete Professional UI/UX Foundations milestone
  - [#2350](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2350): [cueweb] Add Apache 2.0 license header to CueWeb source files
  - [#2349](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2349): [cueweb/docs] Add job comments panel with CRUD and predefined macros
  - [#2348](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2348): [cueweb/docs] Document per-job completion notifications
  - [#2346](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2346): [cueweb] Fix all high and critical npm vulnerabilities
  - [#2341](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2341): [cueweb] Use toast for job-finished notifications and harden poller
  - [#2332](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2332): [cueweb] Bump Next.js to 15.5.18 to patch CVE-2026-44578 (WebSocket SSRF)
  - [#2154](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2154): [docs] Add 2026 project update news and automate nav_order management
  - [#2103](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2103): [sandbox/docs/cueweb/rest_gateway] Add full stack sandbox deployment with CueWeb and REST Gateway
  - [#2098](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2098): [ci/cueweb/rest_gateway] Add Docker build jobs for cueweb and rest_gateway
  - [#2015](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2015): [rest_gateway] Add management interface endpoints and comprehensive testing
  - [#1955](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1955): [docs] Add comprehensive CueWeb documentation with mermaid diagram support
  - [#1596](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1596): [cueweb] CueWeb system: First web-based release of CueGUI with many features from Cuetopia
  - [#1356](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1356): [cueweb] CueWeb system
- [Zach Fong](https://github.com/Zach-Fong): 7 commits
  - [#1439](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1439): [cueweb] Enhance CueWeb search functionality
  - [#1457](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1457): [cueweb] CueWeb improvements and add unit testing
  - [#1578](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1578): [cueweb] Actions, context menu, auto-reload, and search by show-shot
  - [#1580](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1580): [cueweb] Prevent page reload on data updates in jobs, layers, and frames tables
  - [#1592](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1592): [cueweb] Add autoload user jobs, fix frames page, and update interface screenshots
  - [#1623](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1623): [cueweb] Fix autoload and caching
  - [#1596](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1596): [cueweb] CueWeb system: First web-based release of CueGUI with many features from Cuetopia
- [Mariz Fahmy](https://github.com/marizf888): 2 commits
  - [#1356](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1356): [cueweb] CueWeb system
  - [#1596](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1596): [cueweb] CueWeb system: First web-based release of CueGUI with many features from Cuetopia
- [Tomi Lui](https://github.com/tomi-lui): 2 commits
  - [#1356](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1356): [cueweb] CueWeb system
  - [#1596](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1596): [cueweb] CueWeb system: First web-based release of CueGUI with many features from Cuetopia
- [Hai Shun](https://github.com/ttpss930141011): 2 commits
  - [#2391](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2391): [cueweb/docs] Host and Allocation Management: Hosts monitor page - Initial version
  - [#2405](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2405): [cueweb] Job Management actions: min/max cores, batch confirmation, unbook
- [Michael Vallido](https://github.com/mvallido): 2 commits
  - [#2335](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2335): [cueweb] Add per-job subscribe bell for completion notifications
  - [#2404](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2404): [cueweb] Add per-show group tree with drag-to-reparent
- [Mukunda Rao Katta](https://github.com/MukundaKatta): 2 commits
  - [#2330](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2330): [cueweb] Add frame state filter chips
  - [#2331](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2331): [cueweb] Add job progress tooltip
- [Anadee](https://github.com/Anadee11): 1 commit
  - [#2376](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2376): [cueweb] Add Create Show modal
- [Raj Aryan](https://github.com/rajaryan2007): 1 commit
  - [#2377](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2377): [cueweb] Add job dependency graph: inline panel + Cuetopia toggle
- [Vishal Kumar Singh](https://github.com/singhvishalkr): 1 commit
  - [#2336](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2336): [cueweb] Add human-readable age column with smart formatting
- [Jimmy Christensen](https://github.com/lithorus): 1 commit
  - [#2132](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2132): [cueweb/docs] Update cueweb documentation with correct healthcheck using wget instead of curl
- [Alexis Oblet](https://github.com/aoblet): 1 commit
  - [#2096](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2096): [cueweb] Add CueWeb LDAP Authentication
- [Dev Kumar Pal](https://github.com/devkumar2313): 1 commit
  - [#1906](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1906): [cueweb] Add Professional Toolbar with Grouped Action Buttons

Thank you to everyone who contributed with code, reviews, testing, and feedback.

## Get Started

OpenCueWeb is available now on the [OpenCue master branch](https://github.com/AcademySoftwareFoundation/OpenCue). The full documentation set covers OpenCueWeb and the REST Gateway it depends on:

**Quick starts**
- [REST Gateway Quick Start](https://docs.opencue.io/docs/quick-starts/quick-start-rest-gateway/)
- [CueWeb Quick Start](https://docs.opencue.io/docs/quick-starts/quick-start-cueweb/)

**Concepts**
- [CueWeb and REST Gateway](https://docs.opencue.io/docs/concepts/cueweb-rest-gateway/)

**Getting started**
- [Deploying OpenCue REST Gateway](https://docs.opencue.io/docs/getting-started/deploying-rest-gateway/)
- [Deploying CueWeb](https://docs.opencue.io/docs/getting-started/deploying-cueweb/)

**User guides**
- [OpenCue REST Gateway User Guide](https://docs.opencue.io/docs/user-guides/using-rest-api/)
- [CueWeb User Guide](https://docs.opencue.io/docs/user-guides/cueweb-user-guide/)

**Other guides**
- [Production deployment and configuration of the OpenCue REST Gateway](https://docs.opencue.io/docs/other-guides/deploying-rest-gateway/)
- [CueWeb System](https://docs.opencue.io/docs/other-guides/cueweb/)

**Reference**
- [OpenCue REST API Reference](https://docs.opencue.io/docs/reference/rest-api-reference/)
- [CueWeb Reference](https://docs.opencue.io/docs/reference/cueweb/)

**Tutorials**
- [REST API Tutorial](https://docs.opencue.io/docs/tutorials/rest-api-tutorial/)
- [CueWeb Tutorial](https://docs.opencue.io/docs/tutorials/cueweb-tutorial/)

**Developer guide**
- [REST Gateway Development](https://docs.opencue.io/docs/developer-guide/rest-gateway-development/)
- [CueWeb Development Guide](https://docs.opencue.io/docs/developer-guide/cueweb-development/)

## Community and Support

Have questions or feedback about OpenCueWeb?

- **Slack**: Join us in #opencue on [ASWF Slack](https://slack.aswf.io)
- **GitHub Discussions**: [OpenCue Discussions](https://github.com/AcademySoftwareFoundation/OpenCue/discussions)

---

OpenCueWeb brings the full power of CueGUI to the browser, making OpenCue more accessible than ever. Try it out and please file issues and feedback.

Happy rendering!

---

[GitHub Repository](https://github.com/AcademySoftwareFoundation/OpenCue) | [Documentation](https://docs.opencue.io)
