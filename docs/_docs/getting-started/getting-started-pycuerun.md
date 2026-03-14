---
title: "Getting Started with PyCuerun"
nav_order: 33
parent: Getting Started
layout: default
date: 2026-03-13
description: >
  Set up and use pycuerun to submit, inspect, and execute OpenCue outline jobs
  from the command line
---

# Getting Started with PyCuerun

Set up pycuerun and learn the essential commands for submitting and managing OpenCue jobs from the command line.

> **Note:** PyCuerun is the command-line tool for launching jobs defined with [PyOutline](/docs/getting-started/getting-started-pyoutline/), OpenCue's Python job definition library. PyCuerun is included in the PyOutline package — installing PyOutline gives you both the library and the `pycuerun` command.

## Before you begin

You need:

- Python 3.7 or later
- A running Cuebot instance (see [Deploying Cuebot](/docs/getting-started/deploying-cuebot/))
- PyCue and PyOutline installed (see [Installing PyCue and PyOutline](/docs/getting-started/installing-pycue-and-pyoutline/))
- `CUEBOT_HOSTS` environment variable set to your Cuebot hostname

## Step 1: Verify pycuerun is installed

PyCuerun is included with the PyOutline package. Verify it is available:

```bash
pycuerun --help
```

If the command is not found, install PyOutline:

```bash
pip install opencue-pyoutline
```

Or from source:

```bash
cd OpenCue
pip install pyoutline/
```

## Step 2: Create an outline script

Outline scripts are Python files that define job layers. Create a file called `my_job.outline`:

```python
import outline.modules.shell

outline.modules.shell.Shell(
    "hello",
    command=["echo", "Hello from frame #IFRAME#"],
    range="1-10"
)
```

This defines a single layer named "hello" that runs `echo` for frames 1 through 10. The `#IFRAME#` token is replaced with the frame number at execution time.

## Step 3: Inspect the script

Before submitting, inspect the outline to verify its structure:

```bash
pycuerun -i my_job.outline
```

This displays layer names, frame ranges, and dependencies without submitting the job.

## Step 4: Submit the job

Submit the outline to the render farm:

```bash
pycuerun my_job.outline
```

To override the frame range defined in the script:

```bash
pycuerun -f 1-50 my_job.outline
```

## Step 5: Control job behavior

Pycuerun provides flags to control how jobs are submitted and monitored.

### Launch paused

Submit the job but don't start processing until you manually resume it (via CueGUI or PyCue):

```bash
pycuerun -p my_job.outline
```

### Wait for completion

Block the terminal until the job finishes:

```bash
pycuerun -w my_job.outline
```

### Test mode

Block until the job finishes and exit with a non-zero code if any frames fail. Useful for CI/CD:

```bash
pycuerun -t my_job.outline
```

### Set retries and disable email

```bash
pycuerun --max-retries 3 --no-mail my_job.outline
```

## Step 6: Debug a failing frame

If a frame fails on the farm, execute it locally to diagnose the issue:

```bash
pycuerun -e 5-hello my_job.outline
```

The format is `{frame_number}-{layer_name}`. Add `-D` for debug logging:

```bash
pycuerun -D -e 5-hello my_job.outline
```

## Step 7: Run a job locally

For development and testing, run all frames on your local machine instead of the render farm:

```bash
pycuerun --backend local my_job.outline
```

The local backend executes frames sequentially, respecting dependency order.

## Step 8: Submit a multi-layer job

Create `pipeline.outline` with dependencies between layers:

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

Submit it:

```bash
pycuerun pipeline.outline
```

Each composite frame waits for the corresponding render frame to complete before running.

## Step 9: Pass environment variables

Pass runtime configuration to your job:

```bash
pycuerun --env QUALITY=high --env OUTPUT=/renders/final my_job.outline
```

These variables are available in every frame's execution environment.

## Common options reference

| Option | Description |
|--------|-------------|
| `-f RANGE` | Override frame range (e.g., `1-100`, `1-100x5`, `1,5,10`) |
| `-p` | Launch in paused state |
| `-w` | Wait for job completion |
| `-t` | Wait and fail if job fails |
| `-i` | Inspect script without submitting |
| `-e FRAME` | Execute a single frame locally (e.g., `5-layer_name`) |
| `-D` | Enable debug logging |
| `-V` | Enable verbose output |
| `-F FACILITY` | Target a specific facility |
| `-s SERVER` | Set Cuebot server |
| `-o OS` | Target operating system |
| `-b BACKEND` | Set backend (`cue` or `local`) |
| `--env K=V` | Set environment variable (repeatable) |
| `--max-retries N` | Max retries per frame |
| `--no-mail` | Disable email notifications |
| `--shot SHOT` | Override shot context |
| `--base-name NAME` | Override job base name |
| `--autoeat` | Auto-remove dead frames without retry |
| `--qc` | Add QC hold layer for artist review |
