![OpenCue](/images/opencue_logo_with_text.png)

[![Supported VFX Platform Versions](https://img.shields.io/badge/vfx%20platform-2021--2024-lightgrey.svg)](http://www.vfxplatform.com/)
![Supported Python Versions](https://img.shields.io/badge/python-3.6+-blue.svg)
[![CII Best Practices](https://bestpractices.coreinfrastructure.org/projects/2837/badge)](https://bestpractices.coreinfrastructure.org/projects/2837)

- [Introduction](#Introduction)
- [OpenCue features](#OpenCue-features)
- [Learn more](#Learn-more)
- [Meeting notes](#Meeting-notes)
- [Contact us](#Contact-us)

# Introduction

OpenCue is an open source render management system. You can use OpenCue in
visual effects and animation production to break down complex jobs into
individual tasks. You can submit jobs to a configurable dispatch queue that
allocates the necessary computational resources.

# OpenCue features

OpenCue provides the following features to help manage rendering jobs at scale:

- [Sony Pictures Imageworks in-house render manager](https://www.opencue.io/docs/concepts/spi-case-study/)
  used on hundreds of films.
- Highly-scalable architecture supporting numerous concurrent machines.
- Tagging systems allow you to allocate specific jobs to specific machine
  types.
- Jobs are processed on a central render farm and don't rely on the artist's
  workstation.
- Native multi-threading that supports Katana, Prman, and Arnold.
- Support for multi facility, on-premisses, cloud, and hybrid deployments.
- You can split a host into a large number of [procs](https://www.opencue.io/docs/concepts/glossary/#proc), each with their own
  reserved core and memory requirements.
- Integrated automated booking.
- No limit on the number of [procs](https://www.opencue.io/docs/concepts/glossary/#proc) a job can have.

# Learn more

For more information on installing, using, and administering OpenCue, visit
[www.opencue.io](https://www.opencue.io).

Watch YouTube videos on the [OpenCue Playlist](https://www.youtube.com/playlist?list=PL9dZxafYCWmzSBEwVT2AQinmZolYqBzdp) of the Academy Software Foundation (ASWF) to learn more.

# Meeting notes

Starting from May 2024, all Opencue meeting notes are stored on the [Opencue Confluence page](http://wiki.aswf.io/display/OPENCUE/OpenCue+Home).

For meeting notes before May 2024, please refer to the Opencue repository in the [opencue/tsc/meetings](https://github.com/AcademySoftwareFoundation/OpenCue/tree/master/tsc/meetings) folder.

# Contact us

To join the OpenCue discussion forum for users and admins, join the
[opencue-user mailing list](https://lists.aswf.io/g/opencue-user) or email the
group directly at <opencue-user@lists.aswf.io>.

Join the [Opencue Slack channel](https://academysoftwarefdn.slack.com/archives/CMFPXV39Q).
