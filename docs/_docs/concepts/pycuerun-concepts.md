---
title: "PyCuerun Concepts"
nav_order: 20
parent: "Concepts"
layout: default
date: 2026-03-13
description: >
  Core concepts behind pycuerun, the command-line tool for launching and
  executing PyOutline jobs on the OpenCue render farm.
---

# PyCuerun Concepts

Understand how pycuerun works as the bridge between PyOutline scripts and the OpenCue render farm.

> **Note:** PyCuerun is the command-line frontend for [PyOutline](/docs/concepts/pyoutline-concepts/), which is the underlying Python library for defining jobs. PyOutline builds the job specification; pycuerun submits it to the render farm and executes frames on render hosts.

## Overview

PyCuerun is both a command-line tool and a framework for launching PyOutline jobs. It handles the complete lifecycle from script parsing through job submission, and also serves as the frame executor when jobs run on render hosts.

## Core Concepts

### Outline Scripts

An **outline script** is a Python file (`.outline` or `.py`) that defines layers using PyOutline's API. When pycuerun loads a script, it:

1. Creates an implicit `Outline` object (the "current outline")
2. Executes the script, which adds layers to the current outline
3. Returns the fully constructed outline for submission

```python
# my_render.outline
import outline.modules.shell

outline.modules.shell.Shell(
    "render",
    command=["maya", "-render", "scene.ma"],
    range="1-100"
)
```

Outline scripts can also be serialized YAML files (`.yaml`) that pycuerun can load directly.

### The OutlineLauncher

The `OutlineLauncher` is the central class that manages job submission. It encapsulates:

- **The outline**: The job definition to submit
- **Launch flags**: Pause, wait, test, priority, facility, backend, etc.
- **Setup**: Prepares the outline (creates sessions, validates layers)
- **Serialization**: Converts the outline to a backend-specific job spec
- **Launch**: Submits the job to the selected backend

### Dual-Role Execution

PyCuerun serves two distinct roles:

#### 1. Job Launcher

When you run `pycuerun my_script.outline`, it acts as a **launcher**:

```text
pycuerun my_script.outline
    |
    v
Parse outline script --> Setup outline --> Serialize to job spec --> Submit to Cuebot
```

#### 2. Frame Executor

When a job runs on the render farm, Cuebot invokes pycuerun to **execute individual frames**:

```text
pycuerun -e 5-render my_script.outline
    |
    v
Load outline --> Find "render" layer --> Execute frame 5
```

This dual role means pycuerun must be installed on both submission machines and render hosts.

### Job Wrapping

When submitting to the OpenCue backend, pycuerun wraps each layer's command in a chain:

```text
opencue_wrap_frame --> pycuerun -e {frame}-{layer} script.outline
```

The wrapper (`opencue_wrap_frame`) sets up the execution environment (show, shot, paths) before pycuerun executes the specific frame.

### Backend Selection

PyCuerun supports multiple backends:

- **`cue` (default)**: Submits to Cuebot, which dispatches frames to render hosts
- **`local`**: Executes all frames sequentially on the local machine using a SQLite-based dispatcher

The backend is selected by:
1. The `--backend` CLI flag
2. The `outline.backend` configuration setting
3. Defaults to `cue`

### Script Inspection

The inspect mode (`-i`) loads an outline script and displays its structure without submitting:

```bash
pycuerun -i my_script.outline
```

This is useful for validating job structure, checking frame ranges, and debugging outline scripts.

### QC Integration

The `--qc` flag adds a Quality Control layer that:
1. Depends on all other layers in the job
2. Pauses execution, allowing an artist to review results
3. Requires manual intervention to complete or fail the job

### Version Management

PyCuerun supports version pinning for reproducible job execution:

- `--version`: Specify an exact PyOutline version
- `--repos`: Point to a specific repository path
- `--dev` / `--dev-user`: Use development versions for testing
