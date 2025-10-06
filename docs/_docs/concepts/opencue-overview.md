---
title: "OpenCue overview"
nav_order: 10
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
central server clusters. The following list provides a comprehensive summary of all
OpenCue components:

### Core Server Components

*   **Cuebot** - The central management server that performs critical OpenCue tasks including managing job submissions, distributing work to render nodes, and responding to API requests from client tools. Typically runs on a server and can be deployed in clusters for high availability.

*   **RQD (Python)** - The render queue daemon that runs on all rendering hosts. RQD registers hosts with Cuebot, receives work instructions, monitors worker processes, and reports results back to the central server.

*   **Rust RQD** - A high-performance implementation of RQD written in Rust, providing the same functionality as Python RQD with improved performance and resource efficiency.

### Client Applications

*   **CueGUI** - The desktop graphical user interface divided into two main workspaces: Cuetopia (artist-focused job monitoring) and CueCommander (administrator-focused system management). Provides comprehensive tools for job monitoring, frame inspection, host management, and system administration.

*   **CueWeb** - A web-based interface that brings CueGUI's core functionality to the browser. Offers job management, frame monitoring, real-time updates, and collaborative features accessible from anywhere on the network without requiring client installation.

*   **CueSubmit** - A graphical user interface for configuring and launching rendering jobs. Typically runs as a plug-in within 3D software like Maya, Blender, or Nuke, allowing artists to submit jobs directly from their creative applications.

*   **CueAdmin** - Command-line administrative tools for OpenCue system management, providing scripting capabilities for automation, bulk operations, and system maintenance tasks.

*   **Cueman** - A specialized tool for managing and monitoring OpenCue deployments, providing additional administrative capabilities and system oversight functions.

### API and Integration Layer

*   **OpenCue REST Gateway** - A production-ready HTTP service that translates REST API calls to gRPC communication with Cuebot. Enables web applications, scripts, and third-party tools to interact with OpenCue services through standard HTTP endpoints.

*   **PyCue** - The Python API library that provides programmatic access to OpenCue functionality. Used by client applications and custom scripts to interact with Cuebot's gRPC interface.

*   **PyOutline** - A Python library for creating job specifications and render job descriptions. Provides the framework for defining complex rendering workflows and job dependencies.

Figure 1 illustrates how all OpenCue components interact in a comprehensive
deployment, showing the complete ecosystem from artist workstations to render farm hosts.

![Overview of OpenCue architecture and components](/assets/images/opencue_architecture_comprehensive.svg)

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

