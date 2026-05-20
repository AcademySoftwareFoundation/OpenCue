---
title: "PyOutline Quick Start"
nav_order: 6
parent: Quick Starts
layout: default
date: 2026-03-13
description: >
  Get started with PyOutline to build and submit render jobs to OpenCue programmatically
---

# Quick start with PyOutline

Learn how to create and submit your first OpenCue job using PyOutline, OpenCue's Python library for job definition.

## What is PyOutline?

PyOutline is a Python library that provides a high-level interface for constructing OpenCue job definitions. Instead of working directly with job specification XML, you use Python objects to define jobs, layers, frame ranges, and dependencies.

> **Note:** PyOutline works hand-in-hand with [pycuerun](/docs/quick-starts/quick-start-pycuerun/), the command-line tool that submits PyOutline scripts to the render farm. You can launch jobs programmatically via PyOutline's API or from the command line via pycuerun.

## Before you begin

Ensure you have:
- OpenCue sandbox environment running (or a Cuebot deployment)
- Python 3.7 or later installed
- PyCue and PyOutline installed

If not installed:

```bash
pip install opencue-pycue opencue-pyoutline
```

Set the Cuebot host. E.g.: localhost

```bash
export CUEBOT_HOSTS="localhost"
```

## Step 1: Create a simple job

Create a file called `hello_job.py`:

```python
import outline
import outline.modules.shell

# Create an outline (job definition)
ol = outline.Outline("hello-opencue", shot="test", show="testing", user="myuser")

# Add a shell layer that echoes the frame number
layer = outline.modules.shell.Shell(
    "echo-layer",
    command=["echo", "Hello from frame #IFRAME#"],
    range="1-10"
)
ol.add_layer(layer)

# Launch the job
outline.cuerun.launch(ol, use_pycuerun=False, os="Linux")
```

Run the script:

```bash
python hello_job.py
```

This submits a job with 10 frames, each echoing its frame number.

## Step 2: Add dependencies between layers

```python
import outline
import outline.modules.shell

ol = outline.Outline("dependency-job", shot="test", show="testing")

render = outline.modules.shell.Shell(
    "render",
    command=["echo", "Rendering frame #IFRAME#"],
    range="1-10"
)
ol.add_layer(render)

composite = outline.modules.shell.Shell(
    "composite",
    command=["echo", "Compositing frame #IFRAME#"],
    range="1-10"
)
composite.depend_on(render)
ol.add_layer(composite)

outline.cuerun.launch(ol, use_pycuerun=False)
```

Each composite frame waits for the corresponding render frame to complete before running.
