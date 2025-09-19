---
layout: default
title: "v1.11.66 release"
parent: Releases
nav_order: 0
---

# Announcing the release of OpenCue v1.11.66

### OpenCue v1.11.66 release notes

#### Tuesday, September 9, 2025

---

[v1.11.66 of OpenCue](https://github.com/AcademySoftwareFoundation/OpenCue/releases/tag/v1.11.66) is a major release that represents a significant modernization of the OpenCue platform. It includes the following changes and updates:

## Major Features

**🦀 Rust-based RQD Implementation**
- Complete rewrite of RQD (Render Queue Daemon) in Rust for improved performance and reliability
- Includes NIMBY logic, integration tests, and optimized retry mechanisms
- Available as an alternative to the Python RQD implementation

**Loki Integration for Centralized Logging**  
- Added support for Loki log aggregation system for frame logs
- Enables centralized log collection and monitoring across the render farm
- Integrated into both Python and Rust RQD implementations

**Cueman CLI Tool**
- New command-line interface for advanced job and batch management
- Provides enhanced control and automation capabilities for OpenCue operations

**Enhanced Docker Support**
- Added frame recovery logic and GPU mode support for Docker-based rendering
- Improved Docker container handling and resource management
- Better integration with containerized workflows

**Complete Documentation Overhaul**
- Migrated documentation to Jekyll with GitHub Pages hosting
- Modern UI with dark mode support and enhanced navigation
- Comprehensive tutorials and developer guides

**Pip packages published on pypi.org**: [https://pypi.org/search/?q=opencue](https://pypi.org/search/?q=opencue)

Install all Opencue Python packages:
```bash
pip install opencue-cueadmin opencue-cuegui opencue-cueman opencue-cuesubmit opencue-proto opencue-pycue opencue-pyoutline opencue-rqd
```

- [opencue-cueadmin](https://pypi.org/project/opencue-cueadmin/)
  - `pip install opencue-cueadmin`
- [opencue-cuegui](https://pypi.org/project/opencue-cuegui/)
  - `pip install opencue-cuegui`
- [opencue-cueman](https://pypi.org/project/opencue-cueman/)
  - `pip install opencue-cueman`
- [opencue-cuesubmit](https://pypi.org/project/opencue-cuesubmit/)
  - `pip install opencue-cuesubmit`
- [opencue-proto](https://pypi.org/project/opencue-proto/)
  - `pip install opencue-proto`
- [opencue-pycue](https://pypi.org/project/opencue-pycue/)
  - `pip install opencue-pycue`
- [opencue-pyoutline](https://pypi.org/project/opencue-pyoutline/)
  - `pip install opencue-pyoutline`
- [opencue-rqd](https://pypi.org/project/opencue-rqd/)
  - `pip install opencue-rqd`

## Notable Improvements

- **CueSubmit Configuration**: Jobs can now be submitted from configuration files
- **Packaging Refactor**: Split protocols into separate packages for better modularity  
- **CueGUI Enhancements**: Improved monitoring tools, performance optimizations, and new filtering options
- **Dependency Updates**: Updated to latest versions of gRPC, Next.js, and other core dependencies

This release represents a significant modernization of OpenCue with the Rust RQD implementation being the standout feature for performance-critical environments.

## Changes

- [cueweb] Fix autoload and caching [#1623](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1623)
- Bump next from 14.2.14 to 14.2.20 in /cueweb [#1624](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1624)
- Bump next from 14.2.20 to 14.2.22 in /cueweb [#1625](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1625)
- Jimmy Christensen becomes a TSC member [#1629](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1629)
- [rqd] Add frame recovery logic for docker mode [#1614](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1614)
- Upgrade log4j [#1626](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1626)
- Reformat all java files [#1627](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1627)
- Fix python3 related issues on Redirect plugin [#1631](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1631)
- [cuegui] Add Max Threads and Memory Optimizer to Attributes Plugin [#1639](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1639)
- [cuesubmit] Replace PySide2 with qtpy in CueSubmit files [#1640](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1640)
- Update grpcio and grpcio-tools dependencies to version 1.69.0 [#1641](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1641)
- Update version file paths to use VERSION.in [#1642](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1642)
- Bump @sentry/node and @sentry/nextjs in /cueweb [#1647](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1647)
- [cuegui] Remove check for source waiting frames on redirect [#1648](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1648)
- [cuebot] Fix and update triggers for job and layer history management [#1645](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1645)
- [rqd] Refactor runOnDocker and add gpu_mode [#1649](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1649)
- Update upload-artifact to v4 since v3 has been deprecated [#1650](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1650)
- [rqd] Fix Lint error in the rqcore.py [#1653](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1653)
- [cuegui] Fix ThreadPool queue length issue and reduce CueGUI freezing on large jobs [#1652](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1652)
- [rqd] Fix for type hinting that doesn't work in python 3.8 [#1655](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1655)
- Add API example to pyoutline and rqd startup example [#1656](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1656)
- [cuegui] Increase memory and core limits on the redirect widget [#1657](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1657)
- [cuegui] Fix slider performance issue on LayerDialog [#1660](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1660)
- [rqd] Check if uid is valid before launching frame [#1661](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1661)
- [rqd] Change default RQD_BECOME_JOB_USER from True to False [#1659](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1659)
- [rqd] Ensure SP_OS gets updated properly on docker mode [#1662](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1662)
- Fix wrongly reported CUE_HT attribute [#1630](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1630)
- [cuegui] Add "Boot Time" column to HostMonitorTree and update AttributesPlugin to include boot time with year [#1664](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1664)
- [rqd] [cuegui] Add support for Loki for frame logs [#1577](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1577)
- [cuegui] Change color of hosts with REBOOT_WHEN_IDLE status [#1666](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1666)
- [cuegui] Make local booking action opt-out [#1668](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1668)
- [docs] Move /docs to /dev_docs [#1670](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1670)
- [cuegui] Save state of the local booking widget [#1669](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1669)
- [rqd] Ensure source on docker mounted volumes exist [#1673](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1673)
- Small fix for building docs in CI/CD and update sphinx [#1674](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1674)
- [rqd] Feature: RQD use host env vars [#1324](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1324)
- Add cuetopia entrypoint to cuegui [#1676](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1676)
- [requirements] Update PySide6 for Python > 3.11 and macOS compatibility [#1677](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1677)
- [cuegui] Add LockState Filter to "Monitor Hosts" window in CueCommander [#1679](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1679)
- Disable compromised tj-actions/changed-files [#1682](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1682)
- [rqd] Rewrite rqnimby logic [#1680](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1680)
- [cuegui] Fix 'Clear' option in the Lock State filter [#1686](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1686)
- [cuegui] Fix plugin state saving error in Monitor Jobs by adding default getters [#1688](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1688)
- [cuegui] Add "Copy Log Path" option to the "Cuetopia > Monitor Job Details" > Frame data table context menu [#1691](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1691)
- [rqd] Fix process lineage logic [#1689](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1689)
- [rqd] Change exitstatus for failed frames on docker that should be retried [#1692](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1692)
- Add new check for changed files [#1684](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1684)
- Bump next from 14.2.22 to 14.2.26 in /cueweb [#1693](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1693)
- Bump @babel/helpers from 7.25.6 to 7.26.10 in /cueweb [#1683](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1683)
- [cuegui] Add icon to 'View Output in Viewer' action for Jobs, Layers, and Frames context menus [#1695](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1695)
- [cuegui] Add null checks to ServiceDialog to prevent crash on missing service [#1699](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1699)
- [cuegui] Improve Sentry setup to log clearer messages and handle optional import [#1701](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1701)
- [rqd] Fix issue on rssUpdate [#1702](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1702)
- [cuebot] Increase Soft and Hard memory limits [#1703](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1703)
- [cuegui] Apply layer filter in Frame Monitor only on double-click [#1705](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1705)
- [cuegui] Prevent window open state from being overwritten during shutdown [#1707](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1707)
- [cuegui] Fix window state not saved when closing via [X] button [#1709](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1709)
- [rqd] Fix issue on child proc memory calculation [#1710](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1710)
- [cuebot] Fix for nullpointer jobs with `str_loki_url` set to null [#1713](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1713)
- [cuegui] Add dynamic plugin support with initial progress bar plugin [#1712](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1712)
- [pycue] Remove python-six and use native str for type checks [#1723](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1723)
- Shutdown now on docker [#1726](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1726)
- [cueadmin/cuegui/pyoutline/rqd] Remove `six` dependency from CueAdmin, CueGUI, PyOutline, and RQD modules [#1725](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1725)
- [cuegui] Add manual refresh button and spacebar shortcut to Monitor Cue [#1728](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1728)
- [cuegui] Fix log viewer crash on Rocky 9 by launching Vim in xterm with safe flags [#1730](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1730)
- [rqd] Retry NIMBY on a schedule [#1731](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1731)
- [cuegui] Fix rqlog syntax highlighting compatibility on Rocky Linux [#1732](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1732)
- [cuegui] Fix Dependency Wizard navigation for Job-on-Job (JOJ) dependency type [#1734](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1734)
- [rqd] Rework rssUpdate based on sessionid [#1736](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1736)
- [rqd] Remove grpc-fork and pynput warnings [#1737](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1737)
- Cuesubmit jobs from config file [#1284](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1284)
- [cuegui] Fix ServiceDialog by using direct access to service fields [#1740](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1740)
- [rqd] Fix session keyError [#1738](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1738)
- [rqd] Ensure logdir is owned by job user [#1742](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1742)
- Split proto into it's own package and create packages for all python modules [#1681](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1681)
- Bump @babel/runtime from 7.25.6 to 7.27.1 in /cueweb [#1745](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1745)
- [cuegui] Fix handling of "Layer on Simulation Frame" dependency in Depend Wizard [#1747](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1747)
- [cuegui] Increase max width on lineEdit in Monitor Host widget [#1743](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1743)
- Fix client install script after packaging refactor (#1681) [#1748](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1748)
- Improve sandbox install script, pyproject metadata, and update documentation [#1751](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1751)
- Update sandbox README to simplify Python client installation [#1752](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1752)
- Update PyYAML dependency to version 6.0.1 [#1753](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1753)
- [rqd] Fix typo that was causing rqconstants.RQD_USE_ALL_HOST_ENV_VARS to never get overridden by rqd.conf [#1754](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1754)
- Ignore compiled proto files [#1756](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1756)
- Bump next from 14.2.26 to 14.2.30 in /cueweb [#1760](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1760)
- Rust RQD [#1759](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1759)
- [rust/rqd] Implement NIMBY logic [#1766](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1766)
- [rust/rqd] Add clippy check to rust project [#1767](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1767)
- [rust/rqd] Add more protections for accountability issues [#1768](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1768)
- [rust/rqd] Refactor core reservation logic [#1769](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1769)
- [rust/rqd] Handle finished frames before sanitizing reservations [#1770](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1770)
- [rust/rqd] Fix fallback gid to match python's rqd [#1775](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1775)
- [rust/rqd] run_as_user should also set gid [#1776](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1776)
- [cuegui] Fix local booking deeding issue [#1780](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1780)
- Update cuebot base image to OpenJDK 18 slim-bullseye [#1778](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1778)
- Add build pipeline for packaging all OpenCue modules in CI workflow [#1785](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1785)
- [rust] Rust tests without arduino [#1783](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1783)
- [docs] Migrate opencue.io documentation into main OpenCue repo with Jekyll, GitHub Pages, modern UI, dark mode, and tutorial enhancements [#1784](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1784)
- [cueadmin] Add Copyright Contributors to the OpenCue Project [#1787](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1787)
- Update CODEOWNERS [#1781](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1781)
- [rust/rqd] Add integration tests [#1771](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1771)
- [cueman] Cueman CLI for advanced job and batch management in OpenCue [#1791](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1791)
- [docs] Add "Deploying Documentation in Your Fork" section to docs/README.md [#1790](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1790)
- [cueadmin] Fix compiled_proto import on output.py [#1772](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1772)
- CI/CD release refactor [#1779](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1779)
- [CI/CD] Remove redundant step for uploading opencue packages in CI workflow [#1798](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1798)
- [CI/CD] Cicd fix packaging v2 [#1802](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1802)
- [cuegui] Add copy buttons for job, layer, and frame names [#1793](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1793)
- [docs] Add documentation build and test instructions to README.md [#1796](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1796)
- [docs] Add Developer Guide with Sandbox testing instructions [#1797](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1797)
- [docs] Add documentation for Rust-based RQD implementation [#1803](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1803)
- [docs] Fix missing "Toggle Menu" link in sidebar navigation [#1804](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1804)
- [docs] Add Cueman documentation and tutorials [#1801](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1801)
- [cuegui] Add OS filter to Monitor Hosts plugin (CueGUI > CueCommander) [#1795](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1795)
- [docs] Add CueGUI > Cuetopia monitoring system documentation [#1805](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1805)
- [rust/rqd] Add dummy-cuebot as a dev dependency for rqd [#1810](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1810)
- [docs] Standardize Cueman naming convention across documentation [#1806](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1806)
- [docs] Implement independent versioning system with automated metadata [#1811](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1811)
- [rust/rqd] Remove complicated trap logic from frame cmd when not needed [#1813](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1813)
- [docs] Modernize and refine OpenCue docs homepage [#1814](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1814)
- [docs] Add Previous/Next navigation buttons and Docs links to documentation [#1815](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1815)
- [docs] Fix docs.opencue.io redirect and broken asset paths and docs improvements [#1818](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1818)
- [docs] Fix broken Getting Started link in documentation homepage [#1819](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1819)
- [CI/CD] Fix packaging steps (v3) [#1820](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1820)
- [CI/CD] Disable Cueman docker image uploads [#1822](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1822)
- [CI/CD] Re-enable integration test script step in packaging pipeline [#1823](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1823)
- [docs] Add OpenCue History section with project timeline [#1824](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1824)
- [docs] Fix documentation navigation links by removing trailing slashes [#1821](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1821)
- [docs] Fix image paths to remove /OpenCue prefix [#1827](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1827)
- [docs] Update and improve the CueAdmin documentation [#1828](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1828)
- [docs] Fix local documentation preview URL in README [#1830](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1830)
- [docs] Fix Sony Pictures Imageworks (SPI) link in the home page [#1831](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1831)
- [docs] Add CueCommander documentation and fix related references [#1829](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1829)
- [docs] reorganize Developer Guide and add contributing guide [#1832](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1832)
- [docs] Add Other Guides and Developer Guide cards to homepage [#1833](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1833)
- [docs] Rewrite and validate Quick start for Linux guide [#1834](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1834)
- [docs] Redesign community section buttons for improved layout [#1836](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1836)
- [docs] Add `Quick Starts` button to homepage hero section [#1835](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1835)
- [CI/CD] Fix CI Python tests by using python -m pip [#1838](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1838)
- [cuegui] Replace unmonitor buttons with dropdown menu in Monitor Jobs [#1841](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1841)
- [docs] Add OpenCue walkthrough video to documentation pages [#1837](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1837)
- [CI/CD] Update coverage config and simplify coverage report script [#1842](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1842)
- [CI/CD] Refactor release pipeline: verify tags and streamline outputs [#1843](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1843)
- [cuegui] Add descriptive labels to Monitor Jobs action buttons [#1846](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1846)
- [opencue] Update host wrapper: cache lock state and prevent tag duplication [#1847](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1847)
- [cuegui] feat: Replace "Group Dependent" checkbox with "Group By" dropdown [#1849](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1849)
- [cuegui] Fix CueGUI performance issues during window operations in CueCommander [#1851](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1851)
- [cuegui] Fix dependency window sizing for better job name visibility [#1853](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1853)
- [cuegui] Optimize CueGUI > Cuetopia > Monitor Jobs performance for large job lists [#1855](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1855)
- [cuegui] Expand job user colors and add a custom RGB option [#1859](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1859)
- [cuegui] Fix Last Line Output persistence in Frame Monitor Tree [#1857](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1857)
- [rust/rqd] Ensure dummy-cuebot is built before running rqd integration tests [#1863](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1863)
- [CueBot] Fix hitaki data-source outdated attributes [#1861](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1861)
- Bump next from 14.2.30 to 14.2.32 in /cueweb [#1866](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1866)
- Bump tracing-subscriber from 0.3.19 to 0.3.20 in /rust [#1865](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1865)
- [cuebot] Increase jobSpec layer limit [#1867](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1867)
- [CI] remove docker images and cleanup artifact uploads [#1868](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1868)
- [rqd] Add support for specifying network interface for rqd [#1860](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1860)
- [CI] reenable rqd docker image [#1875](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1875)
- [CICD] Add rust/rqd to both packaging and release pipelines [#1874](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1874)
- [CI/CD] Fix issue on Python release pipeline [#1876](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1876)
- [CICD] Fix issue when trying to build rqd from scratch on release step [#1877](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1877)
- [CI] Fix artifact upload [#1878](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1878)
- [rust-rqd] Remove `logger` from RunnerConfig and refactor frame logging paths [#1879](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1879)
- [CI/CD] Update pipelines: switch to PyPI for release [#1880](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1880)
- [CICD] Fix asset path for rust binaries on release pipeline [#1882](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1882)
- [pypi] Update pyproject.toml files with descriptions and README files [#1884](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1884)
- Bump brace-expansion in /cueweb [#1870](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1870)
- [rqd/rust] Loki logger [#1862](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1862)
- [rust/rqd] Optimize retry mechanism and add logging info [#1881](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1881)
- [pypi] Fix TestPyPI upload failures for existing package versions [#1887](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1887)