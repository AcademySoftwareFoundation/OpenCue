---
title: "Troubleshooting rendering"
layout: default
parent: Other Guides
nav_order: 33
linkTitle: "Troubleshooting rendering"
date: 2019-02-22
description: >
  Troubleshoot common rendering problems
---

# Troubleshooting Rendering

### Troubleshoot common rendering problems

---

This page describes tools and techniques for debugging problems with your
renders.

## Jobs aren't picking up

If a job isn't picking up, the most common cause is that the job can't locate a
compatible host, so check the following:

-   The job's facility and layer tags match the host's allocation. A host's
    allocation determines both its facility and default tags. To fix this issue,
    you can change the host's allocation in
    [CueGUI's Monitor Host plugin](/docs/reference/cuegui-reference#managing-hosts).

    For more detail on the terms facility, layer, allocation, and how they
    relate to each other, see the [Glossary](/docs/concepts/glossary).

-   The hosts satisfy the job's minimum resource requirements. You can check a
    job's resource requirements in CueGUI's Monitor Job Details plugin. If your
    hosts don't satisfy the job requirements, you must change that job's
    requirements or launch more powerful hosts.

## Failing frames

[Use CueGUI](/docs/reference/cuegui-reference#viewing-logs) to look at the frame logs, which
provides more detail on the failure.
