---
layout: default
title: "v1.4.11 release"
parent: Releases
nav_order: 1
---

# Announcing the release of OpenCue v1.4.11

### OpenCue v1.4.11 release notes

#### Friday, December 13, 2024

---

[v1.4.11 of OpenCue](https://github.com/AcademySoftwareFoundation/OpenCue/releases/tag/v1.4.11)
includes the following changes and updates:

- Refactor VERSION.in file handling [#1537](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1537)
- [cuegui] Fix CueGUI version handling and improve error handling [#1538](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1538)
- [cuegui] Fix TypeError in Comment viewer: Handle job object as iterable [#1542](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1542)
- [cuegui] Add Rocky 9 log root in cuegui.yaml [#1543](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1543)
- [tests] Change tests to not use setup.py, but use the unittest module directly [#1547](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1547)
- [rqd] Avoid changing dict in place during iteration [#1554](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1554)
- Add script for converting imports in grpc python modules and remove 2to3 [#1557](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1557)
- [cuegui] Fix multiple jobs and frames visualization [#1559](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1559)
- [cuegui] Fix FrameContextMenu and test_rightClickItem to handle NoneType job attribute [#1561](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1561)
- [rqd] Fix keys not iterable since it's a built-in function. [#1564](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1564)
- [cuebot] Move dispatcher memory properties to opencue.properties [#1570](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1570)
- [rqd] Rqd tests were not being executed [#1560](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1560)
- [cuebot] Fix issue [#1572](https://github.com/AcademySoftwareFoundation/OpenCue/issues/1572) [#1573](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1573)
- [cuebot] Fix for bootRun failure running. [#1569](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1569)
- [cuegui] Prevent UI freeze during file preview by implementing subprocess.Popen for non-forking viewer applications [#1576](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1576)
- [rqd] Allow customizing HOME and MAIL environments [#1579](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1579)
- Rest gateway [#1355](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1355)
- [rest_gateway] Enhanced logging and error handling for gRPC gateway initialization [#1586](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1586)
- [docker] Fix building docker images without 2to3 [#1584](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1584)
- [cuebot/rqd] Add feature to run frames on a containerized environment using docker [#1549](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1549)
- [cuebot] Minor fix on dispatch query [#1590](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1590)
- [docker] Update dockerhub readme [#1574](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1574)
- [cuegui/pycue] Fix Local Booking widget [#1581](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1581)
- [rqd/cuebot] Hard and Soft memory limits [#1589](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1589)
- [cueweb] CueWeb system: First web-based release of CueGUI with many features from Cuetopia [#1596](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1596)
- Bump cross-spawn from 7.0.3 to 7.0.6 in /cueweb [#1597](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1597)
- Bump cookie and next-auth in /cueweb [#1598](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1598)
- Bump @sentry/browser and @sentry/nextjs in /cueweb [#1599](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1599)
- Remove enum34 dependency from requirements.txt [#1605](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1605)
- (ci/cd) Drop support for cy2022 [#1603](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1603)
- [cuebot] Convert null value from job.str_os to empty string in SQL [#1600](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1600)
- [RQD] Fix core detection on Windows platforms [#1468](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1468)
- [integration-test] [ci/cd] Fix install-client-sources script [#1588](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1588)
- [ci/cd] Add integration test to testing-pipeline.yml [#1606](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1606)
- Add ASWF OpenCue Playlist, Opencue Slack channel, and Zoom biweekly meeting link in the README [#1607](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1607)
- Bump pywin32 from 224 to 301 in /rqd [#1611](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1611)
- [cuebot] Add missing migration from PR[#1246](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1246) [#1610](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1610)
- Update all to actions/checkout@v4 [#1615](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1615)
- [cuegui] feat: Add job node graph plugin v2 [#1400](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1400)
- [cuegui] Add toggleable option to save settings on exit [#1612](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1612)
- [cuegui] Allow non-alphanumeric characters in limits (eg. _ and -) when editing layers [#1616](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1616)
- [cicd] Fix cuegui and cuesubmit dockerfiles [#1618](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1618)
- Bump nanoid from 3.3.7 to 3.3.8 in /cueweb [#1617](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1617)
- [cicd] Limit dependency for pip package NodeGraphQtPy [#1619](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1619)
- [cicd] Upgrade out of centos7 for cuesubmit and cuegui [#1620](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1620)
- [cicd]Add descriptions to docker hub images [#1621](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1621)
- [cicd] Remove dockerhub comments [#1622](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1622)
