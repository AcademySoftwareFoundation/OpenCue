---
layout: default
title: "January 21, 2026: OpenCue Project Update: Major Releases and 2026 Roadmap"
parent: News
nav_order: 0
---

# OpenCue Project Update: Major Releases and 2026 Roadmap

### OpenCue ASWF Update

#### January 21, 2026

---

The OpenCue Technical Steering Committee is excited to share our project update, highlighting the significant progress, new features, community growth, and roadmap for the year ahead.

## About OpenCue

OpenCue is an open-source render farm management system originally developed by Sony Pictures Imageworks (SPI). It has been used at SPI production for many years, managing workloads for all their movies and animations, and was officially migrated to the open-source on 2019. OpenCue is part of the Academy Software Foundation (ASWF) and continues to evolve with contributions from studios and individuals worldwide.

## Community Highlights (January 2023 - January 2026)

### Growing Contributor Base

Over the past three years, OpenCue has seen remarkable community engagement:

- **538 commits** merged into the project
- **32 active contributors** from various industries
- Average pull request merge time reduced to **8 days**

### Key Contributors

We extend our gratitude to our contributors who have driven OpenCue forward:

Diego Tavares ([DiegoTavares](https://github.com/DiegoTavares)), Ramon Figueiredo ([ramonfigueiredo](https://github.com/ramonfigueiredo)), Brian Cipriano ([bcipriano](https://github.com/bcipriano)), Jimmy Christensen ([lithorus](https://github.com/lithorus)), Kazuki Sakamoto ([splhack](https://github.com/splhack)), Sharif Salah ([sharifsalah](https://github.com/sharifsalah)), Lars van der Bijl ([larsbijl](https://github.com/larsbijl)), Roula Oregan ([roulaoregan-spi](https://github.com/roulaoregan-spi)), Nuwan Jayawardene ([n-jay](https://github.com/n-jay)), Anton Brand ([anton-ubi](https://github.com/anton-ubi)), Akim Ruslanov ([akim-ruslanov](https://github.com/akim-ruslanov)), Kern Attila GERMAIN ([KernAttila](https://github.com/KernAttila)), Aniket ([Aniketsy](https://github.com/Aniketsy)), Larry Gritz ([lgritz](https://github.com/lgritz)), Idris Miles ([IdrisMiles](https://github.com/IdrisMiles)), Christian Smith ([smith1511](https://github.com/smith1511)), George Pollard ([Porges](https://github.com/Porges)), Romain ([romainf-ubi](https://github.com/romainf-ubi)), John Mertic ([jmertic](https://github.com/jmertic)), Dónal McMullan ([donalm](https://github.com/donalm)), Alexis Oblet ([aoblet](https://github.com/aoblet)), Sourabh Singh ([srbhss](https://github.com/srbhss)), JeevaRamanathan ([JeevaRamanathan](https://github.com/JeevaRamanathan)), Rosa Behrens Camp ([RosaBehrensCamp](https://github.com/RosaBehrensCamp)), Petr Kalis ([kalisp](https://github.com/kalisp)), Olivier Evers ([ndeebook](https://github.com/ndeebook)), Marcelo F. Bortolini ([mb0rt](https://github.com/mb0rt)), Filippo ([thegodworm](https://github.com/thegodworm)), Zach Fong ([Zach-Fong](https://github.com/Zach-Fong)), and many others who have contributed code, documentation, and community support.

## 2024 Changes Summary

**200 commits** - A very productive year with major new features.

2024 focused on OpenCue's modernization, introducing web-based interfaces and containerization support. CueWeb brought CueGUI functionality to the browser, alongside a new REST API Gateway that opens OpenCue to modern integration patterns. Docker Jobs support enabled running frames in containerized environments, significantly improving reproducibility and isolation. On the infrastructure side, Cuebot gained Prometheus metrics and HTTP healthchecks for better observability, while RQD received hard/soft memory limits for finer resource control. CueGUI was enhanced with an output viewer, job dependency visualization through the Node Graph plugin, and numerous usability improvements. The year also saw important CI/CD modernization, including dropping CY2022 support and migrating from CentOS 7.

### Major Features (2024)

| Feature | PR | Description |
|---------|-----|-------------|
| **CueWeb** | [#1596](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1596) | First web-based release of CueGUI with Cuetopia features |
| **REST Gateway** | [#1355](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1355) | REST API gateway for OpenCue |
| **Docker Jobs** | [#1549](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1549) | Run frames in containerized Docker environments |
| **Hard/Soft Memory Limits** | [#1589](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1589) | Memory limit controls for RQD |
| **Job Node Graph Plugin** | [#1400](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1400) | Visual job dependency graph |

### Cuebot (2024)

- Prometheus metrics collecting ([#1408](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1408))
- HTTP healthcheck ([#1373](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1373))
- Reserve all cores feature ([#1313](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1313))
- Prevent running frames on Swap memory ([#1497](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1497))
- Selfish services feature ([#1390](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1390))
- Kill job reason tracking ([#1367](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1367))
- Email subscription to jobs ([#1368](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1368))
- New indexes for booking performance ([#1304](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1304))
- Run dispatch queries with preparedStatements ([#1410](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1410))
- Move dispatcher memory properties to opencue.properties ([#1570](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1570))
- Fix auto-retrying killed frames ([#1444](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1444))
- Fix dispatched frame chunk end frame number ([#1467](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1467))

### RQD (2024)

- Sentry support ([#1433](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1433))
- Daemonize option ([#1432](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1432))
- Fix core detection on Windows ([#1468](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1468))
- Fix swap memory on Linux ([#1447](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1447))
- Refactor logging ([#1504](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1504))
- Customizable HOME and MAIL environments ([#1579](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1579))
- Fix permission issues when becoming a user ([#1496](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1496))
- Fix cache spill issue ([#1531](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1531))
- Set uid and gid when creating user ([#1480](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1480))
- Sample Dockerfile with CUDA base image ([#1327](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1327))

### CueGUI (2024)

- Output viewer feature ([#1459](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1459))
- Multiple viewers support ([#1513](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1513))
- Preview checkpointed frames ([#1491](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1491))
- Job user colors ([#1463](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1463))
- Request Core Buttons in MenuActions ([#1477](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1477))
- Save settings on exit option ([#1612](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1612))
- Dynamic version in About menu ([#1517](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1517))
- Optional Sentry support ([#1460](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1460))
- Readonly frames/layers when job finished ([#1455](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1455))
- Override frame state display text/color ([#1246](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1246))
- Fix UI freeze during file preview ([#1576](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1576))
- Local Booking widget fixes ([#1581](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1581))
- Many pagination and monitoring fixes

### CueSubmit (2024)

- Jobs from config file with dynamic widgets ([#1425](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1425))
- Frame range for Blender command ([#1337](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1337))
- Style tree view improvements ([#1285](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1285))

### PyCue (2024)

- Interactive host reboot functions ([#1419](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1419))
- API improvements ([#1418](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1418))
- Fix typeError on criterion search ([#1422](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1422))

### CI/CD & Infrastructure (2024)

- Drop support for cy2022 ([#1603](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1603))
- Upgrade from CentOS 7 for cuesubmit/cuegui ([#1620](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1620))
- Integration tests in testing pipeline ([#1606](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1606))
- Upgrade Gradle to 7.6.2 ([#1393](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1393))
- Update to actions/checkout@v4 ([#1615](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1615))

### Other (2024)

- New email template ([#1382](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1382))
- FileSequence support ([#1396](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1396))
- Multi-comment/email ability ([#1168](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1168))
- Add ASWF playlist, Slack, and Zoom links to README ([#1607](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1607))

---

## 2025 Changes Summary

**287 commits** - Focused on architectural changes and new tooling.

2025 focused on architectural changes to improve performance and scalability. RQD was completely rewritten in Rust, delivering a 5x smaller binary with 50% reduced CPU usage. A new Rust-based Distributed Scheduler was introduced to eliminate database bottlenecks in large-scale deployments. Observability improved with Loki integration for centralized log aggregation and event-driven monitoring with dashboards. New tools like CueNimby (system tray NIMBY control) and Cueman (advanced CLI for job management) were introduced, while CueWeb gained LDAP authentication for enterprise environments. The documentation was migrated into the main repository with a Jekyll-based site featuring dark mode support. All Python modules were published to PyPI for the first time, simplifying installation and dependency management.

### Major Features (2025)

| Feature | PR | Description |
|---------|-----|-------------|
| **Distributed Scheduler** | [#2104](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2104) | Rust-based scheduler eliminating database bottlenecks |
| **Rust RQD** | [#1759](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1759) | Complete rewrite of RQD in Rust (5x smaller, 50% less CPU) |
| **CueNimby** | [#2026](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2026) | System tray application for NIMBY control |
| **Cueman** | [#1791](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1791) | CLI for advanced job and batch management |
| **Cuecmd** | [#2028](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2028) | Module for batch command execution |
| **Loki Integration** | [#1577](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1577) | Log aggregation for frame logs |
| **CueWeb LDAP** | [#2096](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2096) | LDAP authentication for CueWeb |
| **Show Archive Automation** | [#2024](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2024) | Automated show archiving |
| **PyPI Packages** | [#1681](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1681) | Split proto and packages for all Python modules |
| **Event-Driven Monitoring** | [#2086](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2086) | Full metrics, dashboards, and documentation |

### Rust RQD Development (2025)

Complete ground-up rewrite with extensive features:
- NIMBY logic implementation ([#1766](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1766))
- Core reservation refactor ([#1769](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1769))
- Integration tests ([#1771](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1771))
- Loki logger ([#1862](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1862))
- OOM prevention logic with kill frame selection ([#2064](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2064))
- PSS memory measurement option ([#2089](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2089))
- kill_all_frames on nimby_locked ([#2057](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2057))
- Memory bug fixes ([#2093](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2093))
- Clippy checks and accountability protections ([#1767](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1767), [#1768](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1768))

### Distributed Scheduler (2025)

- Initial release with cluster-based organization ([#2104](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2104))
- Documentation for scheduler module ([#2113](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2113))
- Cuebot exclusion list for coexistence ([#2087](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2087))

### Documentation Overhaul (2025)

Major migration and modernization:
- Migrate docs into main repo with Jekyll, GitHub Pages, modern UI, dark mode ([#1784](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1784))
- Comprehensive CueWeb documentation ([#1955](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1955))
- REST Gateway documentation ([#1940](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1940))
- Cuetopia monitoring system docs ([#1805](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1805))
- Cueman documentation and tutorials ([#1801](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1801))
- Rust RQD documentation ([#1803](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1803))
- Developer Guide with Sandbox testing ([#1797](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1797))
- CueCommander and CueAdmin docs ([#1828](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1828), [#1829](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1829))
- OpenCue History section ([#1824](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1824))
- Homepage redesign with Quick Starts ([#1814](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1814), [#1835](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1835))

### Testing Infrastructure (2025)

**CueAdmin unit tests:**
- Format, DependUtil, ActionUtil classes
- Subscription, Host, Allocation management
- Proc management, Job management, Utility functions
- Integration tests ([#2008](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2008))

**Cueman unit tests:**
- Job termination logic, Frame operations
- Query/Listing commands, Command parsing
- Error handling, Memory/Duration filtering
- buildFrameSearch, Layer display formatting
- Integration tests ([#2010](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2010))

**REST Gateway:**
- Comprehensive testing infrastructure ([#1940](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1940), [#2015](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2015))

**Standardization:**
- Test file naming convention to `test_*.py` ([#1952](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1952))

### CueGUI (2025)

**New Features:**
- Dynamic plugin support with progress bar ([#1712](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1712))
- OS filter in Monitor Hosts ([#1795](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1795))
- Copy buttons for job/layer/frame names ([#1793](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1793))
- LockState filter in Monitor Hosts ([#1679](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1679))
- Boot Time column ([#1664](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1664))
- Max Threads and Memory Optimizer ([#1639](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1639))
- Manual refresh button + spacebar shortcut ([#1728](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1728))
- Custom RGB job user colors ([#1859](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1859))
- Group By dropdown replacing checkbox ([#1849](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1849))
- Unmonitor dropdown menu ([#1841](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1841))
- Retry Dead Frames action in Progress Bar ([#1961](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1961))

**Performance:**
- Optimize Monitor Jobs for large job lists ([#1855](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1855))
- Fix ThreadPool queue length issue ([#1652](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1652))
- Fix window operations performance ([#1851](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1851))

**Bug Fixes:**
- 20+ bug fixes for UI, dialogs, and state management

### Cuebot (2025)

- Booking show:facility exclusion list ([#2087](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2087))
- DB optional env vars for custom deployment ([#2076](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2076))
- Multiple delimiters in filter action tag parsing ([#2048](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2048))
- Filter actions for UTIL and PRE layers ([#2050](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2050))
- Increase jobSpec layer limit ([#1867](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1867))
- Update Dockerfile to OpenJDK 18 ([#2074](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2074))

### RQD Python (2025)

- Loki support for frame logs ([#1577](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1577))
- macOS temp directory stats support ([#2023](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2023))
- Network interface specification ([#1860](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1860))
- Rewrite rqnimby logic ([#1680](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1680))
- Frame recovery logic for docker mode ([#1614](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1614))
- GPU mode for docker ([#1649](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1649))
- Process lineage fixes ([#1689](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1689))

### REST Gateway (2025)

- Management interface endpoints ([#2015](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2015))
- Comment management REST endpoints ([#1953](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1953))
- Docker build jobs ([#2098](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2098))
- Full stack sandbox deployment ([#2103](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2103))

### CueWeb (2025)

- LDAP Authentication ([#2096](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2096))
- Professional Toolbar with grouped actions ([#1906](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1906))
- Full stack sandbox deployment ([#2103](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2103))

### CI/CD & Infrastructure (2025)

- Switch to PyPI for releases ([#1880](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1880))
- Rust/RQD in packaging and release pipelines ([#1874](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1874))
- Release pipeline refactor ([#1779](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1779))
- Docker build jobs for cueweb/rest_gateway ([#2098](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2098))
- Apache-2.0 license metadata ([#2039](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2039))
- macOS runners upgrade to macos-14 ([#2099](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2099))

### Other Notable Changes (2025)

- **New TSC member**: Jimmy Christensen ([#1629](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1629))
- Remove `six` dependency from all modules ([#1723](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1723), [#1725](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1725), [#2072](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2072))
- Update grpcio to 1.69.0 ([#1641](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1641))
- Upgrade log4j ([#1626](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1626))
- PySide6 compatibility for Python 3.11+ and macOS ([#1677](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1677))
- Reformat all Java files ([#1627](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1627))

## Upcoming Features and Roadmap

### 2026 Goals

In 2026, our focus shifts to completing the Rust migration, advancing distributed scheduling capabilities, and expanding the platform's reach. We aim to finalize the transition to Rust RQD across all platforms for improved performance and reliability, while evolving the Distributed Scheduler with automatic cluster coordination and self-healing capabilities. On the user experience front, CueWeb will achieve feature parity with the desktop applications, enabling full web-based studio adoption. We're also investing heavily in observability through CueInsight, a new monitoring system with AI-driven analytics, and delivering production-grade GPU support for the growing demand in GPU-accelerated rendering workflows.

1. **Complete Rust RQD Migration**: Full transition to the Rust-based RQD across all platforms
2. **Distributed Scheduler v2**: Automatic cluster distribution with:
   - Central control module for coordinating multiple scheduler instances
   - Dynamic cluster assignment based on workload
   - Automatic scaling and self-healing
   - Load balancing across schedulers

3. **Farm Auto-scaling**: Native autoscaling capabilities for cloud infrastructure optimization
4. **Enhanced CueWeb**: Complete feature parity with CueGUI (Cuetopia/CueCommander), professional UI/UX redesign, and production-ready interface for full studio adoption
5. **CueInsight**: Event-driven monitoring system with real-time dashboards, automated job grading, proactive alerting, and AI-driven analytics for render farm intelligence
6. **Production-Grade GPU Support**: Cross-platform GPU discovery (NVIDIA/Apple Metal), vendor-aware scheduling, per-device telemetry, frame isolation, and comprehensive documentation ([#2036](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2036))

## Case Study: Continued Production Use

OpenCue continues to be the backbone of render farm management at Sony Pictures Imageworks, handling:

- All feature film and animation rendering
- Thousands of concurrent render jobs
- Multi-facility coordination
- Cloud burst capabilities

The Distributed Scheduler was developed directly from production needs to address scaling challenges in large-scale rendering environments.

## Get Involved

### Join the TSC

The OpenCue Technical Steering Committee is actively seeking new members! Join our community to:

- Contribute to cutting-edge render farm technology
- Collaborate with industry professionals
- Shape the future of OpenCue
- Share your expertise and learn from others

### Community Resources

- **Slack**: Join #opencue on [ASWF Slack](https://slack.aswf.io)
- **GitHub**: [AcademySoftwareFoundation/OpenCue](https://github.com/AcademySoftwareFoundation/OpenCue)
- **Documentation**: [docs.opencue.io](https://docs.opencue.io/)

Thank you to the entire OpenCue community for your continued support, contributions, and feedback. Together, we're building the future of open-source render farm management.

Happy rendering!

---

[GitHub Repository](https://github.com/AcademySoftwareFoundation/OpenCue) | [Documentation](https://docs.opencue.io) | [Join the Discussion](https://lists.aswf.io/g/opencue-dev)
