---
layout: default
title: "v0.3.6 release"
parent: Releases
nav_order: 14
---

# Announcing the release of OpenCue v0.3.6

### OpenCue v0.3.6 release notes

#### Thursday, December 12, 2019

---

The database schema was updated with this release, please be sure to run the migrations on any existing database to pick up these changes. See [Applying Database Migrations](/docs/other-guides/applying-database-migrations/) for more information.

This release also updates the Spring Boot dependencies, which forced us to make some changes to the command line flags used when starting cuebot. To specify the database url, username and password for cuebot use the following flags:

```
--datasource.cue-data-source.jdbc-url
--datasource.cue-data-source.username
--datasource.cue-data-source.password
```

For more information, please see [Deploying Cuebot](/docs/getting-started/deploying-cuebot/).

Please note that [#560](https://github.com/AcademySoftwareFoundation/OpenCue/pull/560) created a new `requirements_gui.txt` file that is required when installing CueGUI and CueSubmit. This file is only necessary for graphical applications and can be ignored when installing PyOutline, PyCue, and RQD.

[v0.3.6 of OpenCue](https://github.com/AcademySoftwareFoundation/OpenCue/releases/tag/0.3.6)
includes the following changes and updates:

*   Use dark stylesheet for Windows in [#567](https://github.com/AcademySoftwareFoundation/OpenCue/pull/567).
*   Update install-client-archives.sh in [#566](https://github.com/AcademySoftwareFoundation/OpenCue/pull/566).
*   Update cuesubmit_config.example.yaml in [#569](https://github.com/AcademySoftwareFoundation/OpenCue/pull/569).
*   Add '/spcue/'' prefix back to static content in [#571](https://github.com/AcademySoftwareFoundation/OpenCue/pull/571).
*   Update to jdk11 and spring boot 2.2.1 in [#562](https://github.com/AcademySoftwareFoundation/OpenCue/pull/562).
*   Split graphical requirements out into their own file in [#560](https://github.com/AcademySoftwareFoundation/OpenCue/pull/560).
*   Bump version to 0.3 in [#561](https://github.com/AcademySoftwareFoundation/OpenCue/pull/561).
*   Alter table to increase show length in [#528](https://github.com/AcademySoftwareFoundation/OpenCue/pull/528).
*   Add CCLA and ICLA text in [#551](https://github.com/AcademySoftwareFoundation/OpenCue/pull/551).
*   Fix passing message to kill frame in [#546](https://github.com/AcademySoftwareFoundation/OpenCue/pull/546).
*   CueSubmit Python 3 support in [#558](https://github.com/AcademySoftwareFoundation/OpenCue/pull/558).
*   Add a shots volume to the sandbox in [#533](https://github.com/AcademySoftwareFoundation/OpenCue/pull/533).
*   Add link to SPI case study to README.md in [#540](https://github.com/AcademySoftwareFoundation/OpenCue/pull/540).
