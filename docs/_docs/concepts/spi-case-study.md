---
title: "OpenCue Sony Pictures Imageworks case study"
nav_order: 10
parent: Concepts
layout: default
linkTitle: "OpenCue Sony Pictures Imageworks case study"
date: 2019-10-18
description: >
  How Sony Pictures Imageworks runs OpenCue in production
---

# OpenCue Sony Pictures Imageworks case study

### How Sony Pictures Imageworks runs OpenCue in production?

---

This page provides a case study of how Sony Pictures Imageworks runs OpenCue
on production infrastructure. This case study illustrates an earlier version
of OpenCue prior to open sourcing the project. This case study is aimed at
system admins and other professionals planning to install OpenCue. When
planning a production deployment of OpenCue, you can review this case study
alongside the [OpenCue getting started guide](/docs/getting-started/).

## Before you begin

Many of the OpenCue terms and concepts in this case study are explained in
more detail in the following introductory resources:

*   [OpenCue overview](/docs/concepts/opencue-overview/)
*   [Glossary](/docs/concepts/glossary/)

As you read through this case study, you might find it useful to refer to
these introductory resources.

## System components and specifications

The production deployment consists of the following components:

*   Several [Cuebot](/docs/concepts/glossary/#cuebot) virtual machines (VMs)
    servers
*   A database server that stores data over a Network File System (NFS)
*   A render farm consisting of between 2,500 and 4,000 render nodes,
    including:
    *   Dedicated render nodes running [RQD](/docs/concepts/glossary/#rqd)
    *   Artist workstations, also running RQD
*   A 10 Gb/s network

From their workstations, artists submit jobs to OpenCue through a cluster of
Cuebot servers. The Cuebot servers dispatch individual frames in a job to the
render farm. Cuebot servers also store all persistent state and transactions
in the database server. Figure 1 illustrates how the various OpenCue
infrastructure components interact:

![OpenCue infrastructure components](/assets/images/opencue_spi_infrastructure.svg)

Figure 1. OpenCue infrastructure components

Each Cuebot VM is provisioned as follows:

*   Managed via vSphere platform
*   Allocated 4-core CPUs (Intel Xeon L5640 running at 2.3 GHz)
*   Allocated 8 GB RAM

The database server is provisioned as follows:

*   Runs on a bare metal server
*   Allocated 16-core CPUs (Intel Xeon E5-2670 running at 2.6 GHz)
*   Allocated 128 GB RAM

The back end storage is provisioned as follows:

*   Runs on a NetApp filer
*   Allocated the following types of storage:
    *   Primarily using Serial Attached SCSI (SAS) 10K drives
    *   Some SSD for caching
*   Connected to the database server over NFS

The current dataset occupies approximately 1.2 TB, including 7 years of
historical data.

## See also

To learn more about the production use of OpenCue, see the [recording of the
OpenCue Birds of a Feather roadmap from SIGGRAPH
2019](/blog/2019/09/20/opencue-at-siggraph-recording/). In this recording,
Ben Dines from Sony Pictures Imageworks provides a summary of the development
and use of OpenCue on a number of films.

## What’s next?

*   To plan your production deployment of OpenCue, see the [OpenCue getting
    started guide](/docs/getting-started/).
*   To run OpenCue in a Docker sandbox environment on your workstation, see
    [quick starts](/docs/quick-starts/).
