---
title: "PyCuerun Tutorial"
nav_order: 89
parent: Tutorials
layout: default
date: 2026-03-13
description: >
  A hands-on tutorial for using pycuerun to submit, manage, debug, and
  inspect OpenCue outline jobs from the command line.
---

# PyCuerun Tutorial

This tutorial walks you through common pycuerun workflows, from basic job submission to debugging and advanced usage.

> **Note:** PyCuerun is the CLI tool for submitting and executing jobs defined with [PyOutline](/docs/tutorials/pyoutline-tutorial/), the Python job definition library. PyCuerun loads PyOutline scripts, serializes them into OpenCue job specs, and submits them to Cuebot.

## What You'll Learn

- Submitting outline scripts to OpenCue
- Controlling job behavior with flags
- Debugging failing frames locally
- Inspecting outline scripts
- Using environment variables and backends

## Prerequisites

- OpenCue environment running with at least one RQD host
- PyCue and PyOutline installed
- `CUEBOT_HOSTS` environment variable set

## Setup: Create Test Scripts

Create the following outline scripts for use throughout this tutorial.

**simple_job.outline:**

```python
import outline.modules.shell

outline.modules.shell.Shell(
    "process",
    command=["echo", "Processing frame #IFRAME#"],
    range="1-10"
)
```

**multi_layer.outline:**

```python
import outline.modules.shell

render = outline.modules.shell.Shell(
    "render",
    command=["echo", "Rendering frame #IFRAME#"],
    range="1-20"
)

composite = outline.modules.shell.Shell(
    "composite",
    command=["echo", "Compositing frame #IFRAME#"],
    range="1-20"
)
composite.depend_on(render)
```

## Lesson 1: Basic Submission

Submit a simple job:

```bash
pycuerun simple_job.outline
```

The job is submitted to the default facility and begins processing immediately.

## Lesson 2: Controlling Frame Ranges

Override the script's frame range:

```bash
# Render only frames 1-5
pycuerun -f 1-5 simple_job.outline

# Render every 10th frame
pycuerun -f 1-100x10 simple_job.outline

# Render specific frames
pycuerun -f 1,10,50,100 simple_job.outline
```

## Lesson 3: Job Control Flags

### Paused Launch

Submit paused for manual review before starting:

```bash
pycuerun -p multi_layer.outline
```

Resume the job later through CueGUI or PyCue.

### Wait for Completion

Block until the job finishes:

```bash
pycuerun -w multi_layer.outline
echo "Job finished!"
```

### Test Mode

Useful for CI/CD — exits with error code if the job fails:

```bash
pycuerun -t multi_layer.outline
if [ $? -eq 0 ]; then
    echo "All frames succeeded"
else
    echo "Job had failures"
fi
```

### Combining Flags

```bash
pycuerun -f 1-50 -w --max-retries 3 --no-mail multi_layer.outline
```

## Lesson 4: Inspecting Scripts

View the structure of an outline without submitting:

```bash
pycuerun -i multi_layer.outline
```

This displays layer names, frame ranges, and dependency information — useful for validating complex scripts.

## Lesson 5: Debugging with Local Execution

### Execute a Single Frame

Run a specific frame locally to debug issues:

```bash
# Execute frame 5 of the "render" layer
pycuerun -e 5-render multi_layer.outline
```

The format is `{frame_number}-{layer_name}`.

### Enable Debug Logging

```bash
pycuerun -D -e 5-render multi_layer.outline
```

### Run the Entire Job Locally

Use the local backend to test the full job on your machine:

```bash
pycuerun --backend local multi_layer.outline
```

Frames run sequentially, respecting dependency order.

## Lesson 6: Environment Variables

Pass runtime configuration:

```bash
pycuerun --env QUALITY=high --env ENGINE=arnold simple_job.outline
```

Create a script that uses environment variables:

**env_job.outline:**

```python
import outline.modules.shell

outline.modules.shell.Shell(
    "render",
    command=["echo", "Quality: $QUALITY, Engine: $ENGINE"],
    range="1-5"
)
```

```bash
pycuerun --env QUALITY=production --env ENGINE=arnold env_job.outline
```

## Lesson 7: Facility and Server Options

### Target a Specific Facility

```bash
pycuerun -F cloud_render multi_layer.outline
```

### Specify a Cuebot Server

```bash
pycuerun -s cuebot.example.com multi_layer.outline
```

### Target OS

```bash
pycuerun -o Linux multi_layer.outline
```

## Lesson 8: QC Workflow

Add a quality control hold:

```bash
pycuerun --qc multi_layer.outline
```

This adds a QC layer that depends on all other layers and pauses for artist review. The artist approves or rejects through CueGUI.

## Lesson 9: Development Workflows

### Using Development Versions

Test with your local PyOutline changes:

```bash
pycuerun --dev multi_layer.outline
```

### Pin a Specific Version

```bash
pycuerun -v 1.2.3 multi_layer.outline
```

### Custom Repository

```bash
pycuerun -r /path/to/custom/pyoutline multi_layer.outline
```

## Lesson 10: Practical Workflows

### Batch Render with Notification

```bash
pycuerun -w -f 1-100 --no-mail multi_layer.outline && \
    echo "Render complete" || echo "Render failed"
```

### Quick Test Render

```bash
# Render a subset of frames, wait for result
pycuerun -t -f 1,50,100 multi_layer.outline
```

### Debug-Fix-Resubmit Cycle

```bash
# 1. Inspect the script
pycuerun -i my_render.outline

# 2. Test a single frame locally
pycuerun -D -e 42-render my_render.outline

# 3. Fix the issue in the outline script
# ... edit my_render.outline ...

# 4. Re-test the frame
pycuerun -D -e 42-render my_render.outline

# 5. Submit the full job
pycuerun -w my_render.outline
```

## Quick Reference

| Command | Description |
|---------|-------------|
| `pycuerun script.outline` | Submit a job |
| `pycuerun -f 1-100 script.outline` | Override frame range |
| `pycuerun -p script.outline` | Submit paused |
| `pycuerun -w script.outline` | Wait for completion |
| `pycuerun -t script.outline` | Test mode (fail on error) |
| `pycuerun -i script.outline` | Inspect without submitting |
| `pycuerun -e 5-render script.outline` | Execute single frame |
| `pycuerun -D script.outline` | Debug logging |
| `pycuerun --backend local script.outline` | Run locally |
| `pycuerun --env K=V script.outline` | Set environment |
