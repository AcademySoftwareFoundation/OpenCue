---
title: "PyCuerun Quick Start"
nav_order: 7
parent: Quick Starts
layout: default
date: 2026-03-13
description: >
  Get started with pycuerun to launch outline scripts on the OpenCue render farm
---

# Quick start with pycuerun

Learn how to use pycuerun to submit and execute PyOutline job scripts on the OpenCue render farm.

## What is pycuerun?

PyCuerun is the command-line tool for launching PyOutline scripts to OpenCue. It handles job submission, frame execution, and provides options for pausing, waiting, debugging, and inspecting outline jobs.

> **Note:** PyCuerun depends on [PyOutline](/docs/quick-starts/quick-start-pyoutline/), the Python library that defines job structure. PyOutline builds the job; pycuerun submits it. Both are installed together as part of the `opencue-pyoutline` package.

## Before you begin

Ensure you have:
- OpenCue sandbox environment running
- Python 3.7 or later installed
- PyCue and PyOutline installed (`pip install opencue-pycue opencue-pyoutline`)
- `CUEBOT_HOSTS` environment variable set

## Step 1: Create an outline script

Create a file called `render.outline`:

```python
import outline.modules.shell

outline.modules.shell.Shell(
    "render",
    command=["echo", "Rendering frame #IFRAME#"],
    range="1-10"
)
```

## Step 2: Submit the job

```bash
pycuerun render.outline
```

## Step 3: Customize the submission

Override the frame range:

```bash
pycuerun -f 1-50 render.outline
```

Launch in a paused state (requires manual resume):

```bash
pycuerun -p render.outline
```

Wait for the job to complete before returning:

```bash
pycuerun -w render.outline
```

Submit to a specific facility:

```bash
pycuerun -F my_facility render.outline
```

## Step 4: Inspect a script

View the structure of an outline script without submitting it:

```bash
pycuerun -i render.outline
```

## Step 5: Execute a single frame locally

Execute frame 5 of the "render" layer for debugging:

```bash
pycuerun -e 5-render render.outline
```

## Common options summary

| Option | Description |
|--------|-------------|
| `-f RANGE` | Set frame range (e.g., `1-100`, `1,5,10`) |
| `-p` | Launch paused |
| `-w` | Wait for job completion |
| `-t` | Wait and fail if job fails |
| `-F FACILITY` | Set job facility |
| `-e FRAME` | Execute a specific frame locally |
| `-i` | Inspect script structure |
| `-D` | Enable debug logging |
| `--env k=v` | Set environment variables |
