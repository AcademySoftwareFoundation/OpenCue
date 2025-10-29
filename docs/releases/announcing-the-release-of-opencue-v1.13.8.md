---
layout: default
title: "v1.13.8 release"
parent: Releases
nav_order: 0
---

# Announcing the release of OpenCue v1.13.8

### OpenCue v1.13.8 release notes

#### October 8, 2025

---

To learn how to install and configure OpenCue, see our [Getting Started guide](https://docs.opencue.io/docs/quick-starts).

This release brings a large number of new features, enhancements, bug fixes, and documentation improvements across the OpenCue ecosystem. The highlights include new tools, UI/UX improvements, substantial test coverage, and improved documentation.

## Major Features

- **CueNIMBY: Workstation NIMBY Control**
  Introduced the CueNIMBY application, a system tray tool for more convenient NIMBY (Not In My Back Yard) control on individual workstations, making it easy to interact with render farm availability.
  ([#2026](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2026))

- **cuecmd: Batch Command Execution**
  Added the `cuecmd` module, enabling batch command execution across the render farm, streamlining mass operations and administrative tasks.
  ([#2028](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2028))

- **REST Gateway Improvements**
  - Major expansion of OpenCue's REST Gateway documentation and testing infrastructure
    ([#1940](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1940))
  - New REST endpoints for comment management operations
    ([#1953](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1953))
  - Comprehensive management interface endpoints and end-to-end testing
    ([#2015](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2015))

- **Show Archive Automation**
  Implemented archive automation features to streamline show management.
  ([#2024](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2024))

## User Interface and Usability

- **CueWeb**
  - Professional-style toolbar with grouped action buttons
    ([#1906](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1906))
  - Enhanced documentation with mermaid diagram support
    ([#1955](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1955))

- **CueGUI**
  - Improved Monitor Jobs toolbar UI and restored unmonitor buttons
    ([#1892](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1892))
  - Added "Retry Dead Frames" action to Progress Bar
    ([#1961](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1961))
  - Updated documentation screenshots to match new layouts
    ([#2021](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2021))
  - Multiple fixes for job monitoring, grouped job views, dependency wizard behavior, and UI polish
    ([#1964](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1964)), ([#1976](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1976)), ([#1978](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1978)), ([#1995](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1995)), ([#1968](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1968))
  - Removed "Use Local Cores" option for clarity and workflow improvements
    ([#1959](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1959))

## Quality, Testing, and Stability

- **Increase in Unit and Integration Test Coverage:**
  - **CueAdmin**: Tests for all major command modules, management utilities, and integration scenarios
    ([#1941](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1941)), ([#1982](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1982)), ([#1984](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1984)), ([#1985](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1985)), ([#1988](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1988)), ([#1999](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1999)), ([#2013](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2013)), ([#2012](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2012)), ([#2007](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2007)), ([#2014](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2014)), ([#2008](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2008))
  - **Cueman**: Extensive tests for job logic, frame operations, querying, error handling, filtering, and argument parsing
    ([#1950](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1950)), ([#1971](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1971)), ([#1973](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1973)), ([#1979](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1979)), ([#2004](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2004)), ([#2005](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2005)), ([#2006](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2006)), ([#2010](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2010))
  - **REST Gateway**: CI/CD integration and robust endpoint test coverage
    ([#2018](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2018))
  - Test file naming conventions standardized across the codebase
    ([#1952](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1952))

- **CI/CD Improvements:**
  - Dependency and mock library conflict fixes
    ([#1991](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1991))
  - Docs and pipeline reliability improvements
    ([#1997](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1997)), ([#2033](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2033)), ([#2034](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2034))

## Documentation and Ecosystem

- **Documentation Enhancements and Corrections:**
  - New, comprehensive documentation for CueWeb, REST Gateway, and CueProgBar
    ([#1955](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1955)), ([#1940](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1940)), ([#1962](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1962))
  - Improved navigation, release notes, and contributor information
    ([#1937](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1937)), ([#1895](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1895)), ([#1944](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1944)), ([#2030](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2030))

- **Sample and Dockerfile Updates:**
  - Blender and BForArtist Dockerfiles updated to latest LTS with CUDA; improved development workflows
    ([#2003](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2003)), ([#2020](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2020)), ([#2032](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2032))

## Other Improvements and Fixes

- **Platform and Dependency:**
  - Windows newline support, Ruby REXML bump, and PyPI packaging fixes
    ([#2011](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2011)), ([#1951](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1951)), ([#1884](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1884)), ([#1887](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1887)), ([#1949](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1949))
  - macOS temp directory stats for RQD
    ([#2023](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2023))
  - Logging and overload prevention in RQD
    ([#2019](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2019))

- **Job, Frame, and Group Management:**
  - Numerous enhancements and fixes to job monitoring, dependent job collapse, progress dialogs, and job/group operations
    ([#1966](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1966)), ([#5b4231bc](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1978)), ([#3a0cafe](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1995)), ([#14367a9](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1968))

## Changes

- Bump brace-expansion in /cueweb [#1870](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1870)
- [pypi] Update pyproject.toml files with descriptions and README files [#1884](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1884)
- [pypi] Fix TestPyPI upload failures for existing package versions [#1887](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1887)
- [cuegui] Improve Monitor Jobs toolbar UI and restore unmonitor buttons [#1892](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1892)
- [docs] Add "Contributors" section and fix spelling and consistency issues in README [#1937](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1937)
- [rest_gateway] Add comprehensive OpenCue REST Gateway documentation and testing infrastructure [#1940](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1940)
- [docs] Add v1.11.66 release notes documentation [#1895](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1895)
- Update the description of the Opencue modules' README files [#1890](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1890)
- [docs] Fix documentation navigation order and remove duplicate video [#1942](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1942)
- [cueadmin] Add Unit Tests for Format Module Functions [#1941](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1941)
- [docs] OpenCue documentation stable version - Update docs version to 1.11.66 [#1946](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1946)
- [docs] Add News: OpenCue Project Review 2025 [#1948](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1948)
- [pypi] Fix Python package descriptions exceeding 512 character limit [#1949](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1949)
- [cueman] Add Comprehensive Unit Tests for Job Termination Logic in cueman [#1950](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1950)
- [docs] Fix markdown formatting issue in v1.11.66 release notes [#1944](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1944)
- Bump rexml from 3.4.1 to 3.4.2 in /docs [#1951](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1951)
- [cueadmin/cuegui/cuesubmit/pycue/pyoutline/rqd] Standardize test file naming convention to test_*.py [#1952](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1952)
- [rest_gateway] Add REST endpoints for comment management operations [#1953](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1953)
- Update README file [#1956](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1956)
- [cueweb] Add Professional Toolbar with Grouped Action Buttons [#1906](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1906)
- [docs] Add comprehensive CueWeb documentation with mermaid diagram support [#1955](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1955)
- [cueman] Add comprehensive test infrastructure and update documentation for Cueman [#1954](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1954)
- [cuegui] Add 'Retry Dead Frames' action to Progress Bar window [#1961](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1961)
- [cuegui] Fix KeyError when unmonitoring finished/archived jobs [#1964](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1964)
- [docs] Add CueProgBar documentation to Cuetopia monitoring guide [#1962](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1962)
- [cuegui] Fix progress dialog close buttons and completion behavior [#1968](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1968)
- [cuegui] Fix Group Dependent functionality to properly collapse dependent jobs [#1966](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1966)
- [cuegui] Remove "Use Local Cores" option from Layer and Frame context menus [#1959](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1959)
- [cuegui] Fix AttributeError when clicking on GroupWidgetItem in JobMonitorTree [#1976](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1976)
- [cueman] Add Unit Tests for Layer Display Formatting [#1971](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1971)
- [cueman] Add Comprehensive Unit Tests for buildFrameSearch [#1973](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1973)
- [cueadmin] Add unit tests for allocation management [#1974](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1974)
- [cueman] Add Unit Tests for Job Operation Commands [#1979](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1979)
- [cueadmin] Add Unit Tests for Host Management Commands [#1969](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1969)
- [cuegui] Fix Unmonitor Finished feature for grouped job views [#1978](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1978)
- [cueadmin] Enhance testing infrastructure, tooling, and documentation [#1982](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1982)
- [CI/CD] Fix mock dependency conflicts across Python packages [#1991](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1991)
- [cuegui] Fix dependency wizard progress dialog hanging at 100% for grouped jobs [#1995](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1995)
- [CI/CD] Fix docs pipeline failing on tag deployments [#1997](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1997)
- [cueadmin] Add Unit Tests for Subscription Management [#1984](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1984)
- [cueman] Add Unit Tests for Query and Listing Commands [#1988](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1988)
- [cueman] Add unit tests and validation for frame operations [#1999](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1999)
- [Windows] Force newline style [#2011](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2011)
- [cueadmin] Add Unit Tests for DependUtil Class [#1985](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1985)
- Revised the sample rqd blender to latest LTS release with cuda support and added an additional bforartist dockerfiles [#2003](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2003)
- [cueadmin] Add unit tests for proc management commands [#2013](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2013)
- [cueadmin] Add unit tests for utility functions [#2012](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2012)
- [cueadmin] Add unit tests for ActionUtil class and fix protobuf field names [#2007](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2007)
- [cueman] Add comprehensive unit tests for command line argument parsing [#2006](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2006)
- [cueman] Add unit tests for error handling and logging [#2005](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2005)
- [cueman] Add Unit Tests for Memory and Duration Filtering [#2004](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2004)
- [cueadmin] Add job management commands, job unit tests, update integration tests and documentation [#2014](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2014)
- [cueadmin] Add integration tests for CueAdmin [#2008](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2008)
- [rest_gateway] Add management interface endpoints and comprehensive testing [#2015](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2015)
- [cueman] Add integration tests for Cueman [#2010](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2010)
- [CI/CD] Add REST Gateway tests to CI/CD pipeline [#2018](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2018)
- Update CueGUI documentation screenshots to reflect new button layouts [#2021](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2021)
- [rqd] Avoid overloaded log files created by RQD's jobs [#2019](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2019)
- [rqd] Add macOS support for temp directory stats reporting [#2023](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2023)
- [cuebot/pycue/cueadmin/docs] Add show archive automation feature [#2024](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2024)
- [cuebot] Add `onframe` element to dtd spec [#2001](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2001)
- [cueman] Improve input validation and refactor duration/memory filters [#2022](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2022)
- [cuecmd] Add cuecmd module for batch command execution on render farm [#2028](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2028)
- [cuenimby] Add CueNIMBY - System tray application for workstation NIMBY control [#2026](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2026)
- Revised sample rqd blender&cuda+additional bforartist dockerfile [#2020](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2020)
- [docker] Use build for Cuebot in docker-compose for development [#2032](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2032)
- [docs] Update Docs nav_order and some titles [#2030](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2030)
- [CICD] Simplify release pipeline under a single environment [#2033](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2033)
- [CICD] Remove published whls from release [#2034](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2034)
