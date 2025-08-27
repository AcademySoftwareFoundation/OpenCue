---
title: "OpenCue overview"
nav_order: 7
parent: Concepts
layout: default
linkTitle: "OpenCue overview"
date: 2019-02-22
description: >
  An introduction to OpenCue
---

# OpenCue overview

### An introduction to OpenCue

---

## What is OpenCue?

OpenCue is an open source render management system. You can use OpenCue in
visual effects and animation production to break down complex jobs into
individual tasks. You can submit jobs to a configurable dispatch queue that
allocates the necessary computational resources.

## Why use OpenCue?

OpenCue provides features to manage rendering jobs at scale:

*   Sony Pictures Imageworks
    [in-house render manager](/docs/concepts/spi-case-study/) used on
	hundreds of films.
*   Highly-scalable architecture supporting numerous concurrent machines.
*   Tagging systems allow you to allocate specific jobs to specific machine
    types.
*   Jobs are processed on a central render farm and don't rely on the artist's
    workstation.
*   Native multithreading that supports Katana, RenderMan, and Arnold.
*   Support for multi facility, on-premise, cloud, and hybrid deployments.
*   You can split a host into a large number of procs, each with their own
    reserved core and memory requirements.
*   Integrated automated booking.
*   No limit on the number of procs a job can have.

## OpenCue architecture

OpenCue includes components that run on both an artist's workstation, as well as
central server clusters. The following list provides a brief summary of the main
components:

*   Cuebot - a utility that runs in the background on a workstation and performs
    a variety of important OpenCue management tasks. Cuebot can also run in a
    server cluster for high availability.

*   CueGUI - a graphical user interface that artists run to monitor and manage
    jobs.

*   CueSubmit - a graphical user interface for configuring and launching
    rendering jobs to an OpenCue deployment. Artists typically run CueSubmit as
    a plug-in for their 3D software on their workstation.

*   RQD - a software daemon that runs on all rendering hosts, which are doing
    work for an OpenCue deployment.

Figure 1 illustrates how the various components interact in a large-scale
deployment of OpenCue.

![Overview of OpenCue architecture and components](/assets/images/opencue_architecture.svg)

## What's next?

For information on installing OpenCue components and dependencies, see
[Getting started](/docs/getting-started).

To learn common terminology used in OpenCue, see the [Glossary](/docs/concepts/glossary).

Watch YouTube videos on the [OpenCue Playlist](https://www.youtube.com/playlist?list=PL9dZxafYCWmzSBEwVT2AQinmZolYqBzdp) of the Academy Software Foundation (ASWF) to learn more.

## Contact us

To join the OpenCue discussion forum for users and admins, join the
[opencue-user mailing list](https://lists.aswf.io/g/opencue-user) or email the
group directly at <opencue-user@lists.aswf.io>.

Join the [Opencue Slack channel](https://academysoftwarefdn.slack.com/archives/CMFPXV39Q).

Working Group meets biweekly at 2pm PST on [Zoom](https://www.google.com/url?q=https://zoom-lfx.platform.linuxfoundation.org/meeting/95509555934?password%3Da8d65f0e-c5f0-44fb-b362-d3ed0c22b7c1&sa=D&source=calendar&ust=1717863981078692&usg=AOvVaw1zRcYz7VPAwfwOXeBPpoM6).

