![OpenCue](/images/opencue_logo_with_text.png)

[![Supported VFX Platform Versions](https://img.shields.io/badge/vfx%20platform-2021--2024-lightgrey.svg)](http://www.vfxplatform.com/)
![Supported Python Versions](https://img.shields.io/badge/python-3.6+-blue.svg)
[![CII Best Practices](https://bestpractices.coreinfrastructure.org/projects/2837/badge)](https://bestpractices.coreinfrastructure.org/projects/2837)

- [Introduction](#Introduction)
- [OpenCue features](#OpenCue-features)
- [Learn more](#Learn-more)
- [OpenCue documentation](#opencue-documentation)
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

# Quick installation and tests

Read the [OpenCue sandbox documentation](https://github.com/AcademySoftwareFoundation/OpenCue/blob/master/sandbox/README.md) 
to learn how to set up a local OpenCue environment.

- The sandbox environment offers an easy way to run a test OpenCue deployment locally, with all components running in 
separate Docker containers or Python virtual environments.
- It is ideal for small tests, development work, and for those new to OpenCue who want a simple setup for 
experimentation and learning.

To learn how to run the sandbox environment, see https://www.opencue.io/docs/quick-starts/.

# OpenCue full installation

Guides for system admins deploying OpenCue components and installing dependencies are available in the 
[OpenCue documentation](https://www.opencue.io/docs/getting-started/).

# OpenCue documentation

OpenCue documentation is built with Jekyll and hosted on GitHub Pages. The documentation includes installation guides, user guides, API references, and tutorials to help users get started with OpenCue.

When contributing to OpenCue, please update the documentation for any new features or changes. Each pull request should include relevant documentation updates when applicable.

## Building and Testing Documentation

If you make changes to `OpenCue/docs`, please build and test the documentation before submitting your PR:

1. **Build and validate the documentation**
   ```bash
   ./docs/build.sh
   ```

2. **Install bundler binstubs (if needed)**
   
   If you encounter permission errors when installing to system directories:
   ```bash
   cd docs/
   bundle binstubs --all
   ```

3. **Run the documentation locally**
   ```bash
   cd docs/
   bundle exec jekyll serve --livereload
   ```

4. **Preview the documentation**
   
Open http://localhost:4000 in your browser to review your changes.

For detailed documentation setup instructions, testing procedures, and contribution guidelines, see [docs/README.md](https://github.com/AcademySoftwareFoundation/OpenCue/blob/master/docs/README.md).

**Note:** Once your pull request is merged into master, the documentation will be automatically deployed via GitHub Actions ([.github/workflows/docs.yml](https://github.com/AcademySoftwareFoundation/OpenCue/blob/master/.github/workflows/docs.yml)). The updated documentation will be available at https://docs.opencue.io/.

The OpenCue documentation is now available at https://docs.opencue.io/.

# Meeting notes

Starting from May 2024, all Opencue meeting notes are stored on the [Opencue Confluence page](http://wiki.aswf.io/display/OPENCUE/OpenCue+Home).

For meeting notes before May 2024, please refer to the Opencue repository in the [opencue/tsc/meetings](https://github.com/AcademySoftwareFoundation/OpenCue/tree/master/tsc/meetings) folder.

# Contact us

To join the OpenCue discussion forum for users and admins, join the
[opencue-user mailing list](https://lists.aswf.io/g/opencue-user) or email the
group directly at <opencue-user@lists.aswf.io>.

Join the [Opencue Slack channel](https://academysoftwarefdn.slack.com/archives/CMFPXV39Q).

Working Group meets biweekly at 2pm PST on [Zoom](https://www.google.com/url?q=https://zoom-lfx.platform.linuxfoundation.org/meeting/95509555934?password%3Da8d65f0e-c5f0-44fb-b362-d3ed0c22b7c1&sa=D&source=calendar&ust=1717863981078692&usg=AOvVaw1zRcYz7VPAwfwOXeBPpoM6).
