---
title: "PyCuerun User Guide"
nav_order: 48
parent: "User Guides"
layout: default
date: 2026-03-13
description: >
  User guide for the pycuerun command-line tool, covering job submission,
  frame execution, debugging, and advanced options.
---

# PyCuerun User Guide

This guide covers the full capabilities of pycuerun for submitting and managing OpenCue jobs from the command line.

> **Note:** PyCuerun is the CLI frontend for [PyOutline](/docs/user-guides/pyoutline-user-guide/), the Python library that defines job structure (outlines, layers, dependencies). PyCuerun loads PyOutline scripts, serializes them, and submits them to the render farm. Both ship in the same `opencue-pyoutline` package.

## Basic Usage

### Submitting a Job

```bash
pycuerun [options] outline_script [frame_range]
```

The simplest invocation:

```bash
pycuerun my_render.outline
```

### Specifying a Frame Range

Override the script's default frame range:

```bash
pycuerun -f 1-100 my_render.outline
```

Or pass the frame range as a positional argument:

```bash
pycuerun my_render.outline 1-100
```

Frame range formats:

| Format | Meaning |
|--------|---------|
| `1-100` | Frames 1 through 100 |
| `1-100x5` | Every 5th frame (1, 6, 11, ...) |
| `1,5,10,20` | Specific frames |
| `1-50,75-100` | Multiple ranges |

If no range is specified, pycuerun uses the `$FR` environment variable.

## Job Control Options

### Paused Launch

Launch the job in a paused state. Frames will not begin processing until you manually resume:

```bash
pycuerun -p my_render.outline
```

### Wait for Completion

Block the terminal until the job finishes:

```bash
pycuerun -w my_render.outline
```

### Test Mode

Block until completion and return a non-zero exit code if any frames fail:

```bash
pycuerun -t my_render.outline
```

This is useful in CI/CD pipelines or automated workflows.

### Retry Control

Set the maximum number of retries per frame:

```bash
pycuerun --max-retries 3 my_render.outline
```

### Auto-Eat Dead Frames

Automatically remove dead frames without retrying:

```bash
pycuerun --autoeat my_render.outline
```

### Disable Email

Suppress email notifications:

```bash
pycuerun --no-mail my_render.outline
```

## Target Configuration

### Facility

Route the job to a specific facility:

```bash
pycuerun -F cloud_render my_render.outline
```

### Operating System

Target a specific OS for execution:

```bash
pycuerun -o Linux my_render.outline
```

### Server

Specify a Cuebot server:

```bash
pycuerun -s cuebot.example.com my_render.outline
```

### Shot Override

Run the job under a different shot context:

```bash
pycuerun --shot sh020 my_render.outline
```

### Job Base Name

Override the job's base name:

```bash
pycuerun --base-name custom-job-name my_render.outline
```

## Debugging and Development

### Inspect a Script

View the structure of an outline script without submitting:

```bash
pycuerun -i my_render.outline
```

This displays layer names, frame ranges, and dependencies.

### Execute a Single Frame

Run a specific frame locally for debugging:

```bash
pycuerun -e 5-render my_render.outline
```

The format is `{frame_number}-{layer_name}`.

### Debug Mode

Enable debug logging:

```bash
pycuerun -D my_render.outline
```

### Verbose Output

Enable verbose output:

```bash
pycuerun -V my_render.outline
```

### Development Mode

Test with your local development version of PyOutline:

```bash
pycuerun --dev my_render.outline
```

Or test with another user's development version:

```bash
pycuerun --dev-user colleague my_render.outline
```

## Environment Variables

### Setting Variables

Pass environment variables to the job:

```bash
pycuerun --env QUALITY=high --env RENDER_ENGINE=arnold my_render.outline
```

### Key Environment Variables

| Variable | Purpose |
|----------|---------|
| `CUEBOT_HOSTS` | Cuebot server address |
| `SHOW` | Default show name |
| `SHOT` | Default shot name |
| `FR` | Default frame range |
| `RENDER_TO` / `FACILITY` | Default facility |
| `OL_VERSION` | PyOutline version override |

## Backend Selection

### OpenCue Backend (default)

Submit to the Cuebot render farm:

```bash
pycuerun -b cue my_render.outline
```

### Local Backend

Execute frames locally for testing:

```bash
pycuerun -b local my_render.outline
```

The local backend runs frames sequentially using a SQLite dispatcher and respects dependency order.

## QC Integration

Add a Quality Control layer that pauses the job for artist review:

```bash
pycuerun --qc my_render.outline
```

This adds a `wait_on_artist_to_qc` layer that depends on all other layers and pauses execution for review.

## Plugin Options

### Local Cores

Book local machine resources for frame execution:

```bash
pycuerun -L 4 my_render.outline
```

### Local Thread Count

Set threads per frame for local execution:

```bash
pycuerun -T 2 my_render.outline
```

## Version Management

### Pin a Specific Version

```bash
pycuerun -v 1.2.3 my_render.outline
```

### Specify a Repository Path

```bash
pycuerun -r /path/to/pyoutline my_render.outline
```

## Common Workflows

### Render and Wait

```bash
pycuerun -w -f 1-100 --max-retries 3 my_render.outline
```

### CI/CD Test Submission

```bash
pycuerun -t --no-mail -f 1-10 my_render.outline || echo "Job failed"
```

### Debug a Failing Frame

```bash
# First inspect the script
pycuerun -i my_render.outline

# Then execute the failing frame locally with debug logging
pycuerun -D -e 42-render my_render.outline
```

### Paused Review Workflow

```bash
# Launch paused for artist review
pycuerun -p --qc my_render.outline

# Artist reviews and resumes via CueGUI
```
