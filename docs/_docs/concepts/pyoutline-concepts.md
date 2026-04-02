---
title: "PyOutline Concepts"
nav_order: 19
parent: "Concepts"
layout: default
date: 2026-03-13
description: >
  Core concepts behind PyOutline, including outlines, layers, frames,
  dependencies, sessions, and the plugin system.
---

# PyOutline Concepts

Understand the core architecture and concepts of PyOutline, OpenCue's Python library for defining render farm jobs.

> **Note:** PyOutline is the job definition library; [pycuerun](/docs/concepts/pycuerun-concepts/) is its command-line companion that launches PyOutline scripts to the render farm and executes individual frames on render hosts. Together they form OpenCue's Python-based job submission pipeline.

## Overview

PyOutline provides a Python API for constructing OpenCue job specifications. Rather than writing XML directly, you define jobs as Python objects that PyOutline serializes into the format Cuebot understands.

## Core Concepts

### Outlines

An **Outline** is the top-level container for a job definition. It maps directly to an OpenCue job and holds:

- **Name**: The job name (used by Cuebot)
- **Show/Shot/User**: Metadata that determines resource allocation and billing
- **Frame range**: The default range applied to all layers
- **Layers**: The tasks that compose the job
- **Environment variables**: Applied to all layers in the job
- **Facility**: Where the job should run

```python
ol = outline.Outline("my-render", show="myshow", shot="sh010", user="artist")
ol.set_frame_range("1-100")
```

### Layers

A **Layer** represents a distinct task type within a job. Each layer defines:

- **Command**: What to execute for each frame
- **Frame range**: Which frames to process (inherits from outline if not set)
- **Type**: `RENDER`, `UTIL`, or `POST`
- **Chunk size**: How many frames to process per task
- **Resource requirements**: Cores, memory, GPU

```python
layer = Shell("render", command=["maya", "-render", "scene.ma"], range="1-100")
```

#### Layer Types

| Type | Purpose | Example |
|------|---------|---------|
| `RENDER` | Primary rendering work | Maya renders, Nuke composites |
| `UTIL` | Utility/support tasks | File transfers, conversions |
| `POST` | Post-job cleanup | Notification, archival |

#### Specialized Layer Classes

- **`Layer`**: Base class for custom layers (subclass and override `_execute`)
- **`Frame`**: A single-frame layer, immune from frame range intersection
- **`LayerPreProcess`**: Runs before its parent layer, can store outputs for parent consumption
- **`LayerPostProcess`**: Runs after its parent layer completes
- **`OutlinePostCommand`**: Runs after the entire job completes

### Frames

A **Frame** is the smallest unit of work. Each frame within a layer represents one execution of the layer's command with a specific frame number. The `#IFRAME#` token in commands gets replaced with the current frame number at execution time.

```text
Layer "render" with range 1-10:
  Frame 1: maya -render -s 1 -e 1 scene.ma
  Frame 2: maya -render -s 2 -e 2 scene.ma
  ...
  Frame 10: maya -render -s 10 -e 10 scene.ma
```

### Frame Ranges and Chunking

**Frame ranges** specify which frames a layer processes:

```python
layer.set_frame_range("1-100")       # Frames 1 through 100
layer.set_frame_range("1-100x5")     # Every 5th frame: 1,6,11,...
layer.set_frame_range("1,5,10,20")   # Specific frames
```

**Chunking** groups multiple frames into a single task:

```python
layer.set_chunk_size(5)
# Range 1-20 with chunk=5 creates 4 tasks:
#   Task 1: frames 1-5
#   Task 2: frames 6-10
#   Task 3: frames 11-15
#   Task 4: frames 16-20
```

This is useful when the startup cost of your application is high relative to per-frame processing time.

### Dependencies

Dependencies control execution order between layers. PyOutline supports several dependency types:

#### Frame-by-Frame (default)

Each frame in the dependent layer waits for the corresponding frame in the dependency layer:

```python
composite.depend_on(render)
# composite frame 5 waits for render frame 5
```

#### Layer-on-Layer

All frames in the dependent layer wait for all frames in the dependency layer:

```python
composite.depend_all(render)
# No composite frame runs until all render frames complete
```

#### Previous Frame

Each frame waits for the previous frame in the dependency layer (useful for simulations):

```python
sim_layer.depend_previous(sim_layer)
# Frame N waits for frame N-1
```

#### Any Frame

The dependency is satisfied when any single frame in the dependency layer completes:

```python
layer.depend_on(setup_layer, "any")
```

### Sessions

A **Session** provides persistent storage for a job's runtime data. Sessions are created automatically during job setup and provide:

- **File storage**: Copy or symlink files into the session for frame access
- **Data exchange**: Serialize/deserialize Python data (via YAML) between frames
- **Per-layer directories**: Isolated storage for each layer

```python
# Store data from one frame
layer.put_data("result", {"status": "complete", "output": "/path/to/file"})

# Retrieve in another frame or layer
data = layer.get_data("result")
```

Session directories are stored at `~/.opencue/sessions/<show-shot-user>/<uuid>/`.

### Outline Lifecycle

An outline progresses through three modes:

```text
INIT  -->  SETUP  -->  READY
```

1. **INIT**: The outline script is parsed, layers are created and added
2. **SETUP**: Session directories are created, files are staged, layers are validated
3. **READY**: The outline is serialized and submitted to the backend

### Backends

PyOutline supports pluggable backends for job execution:

| Backend | Description | Use Case |
|---------|-------------|----------|
| `cue` | Submits to Cuebot via OpenCue API | Production rendering |
| `local` | Executes frames sequentially on the local machine | Development and testing |

The backend is selected via configuration or the `--backend` flag.

### Environment Variables

Environment variables can be set at two levels:

- **Outline level**: Applied to all layers in the job
- **Layer level**: Applied only to that specific layer

```python
ol.set_env("RENDER_QUALITY", "high")           # All layers
layer.set_env("NUKE_PATH", "/path/to/plugins")  # This layer only
```

### Plugin System

PyOutline supports a plugin architecture for extending behavior:

- Plugins are registered in the configuration file under `[plugin:name]` sections
- Plugins can hook into layer initialization, launch events, and CLI option parsing
- The `PluginManager` loads and manages all registered plugins

### Events

The event system provides lifecycle hooks:

| Event | When |
|-------|------|
| `AFTER_INIT` | After layer initialization |
| `AFTER_PARENTED` | After layer is added to an outline |
| `SETUP` | During outline setup phase |
| `BEFORE_EXECUTE` | Before frame execution |
| `AFTER_EXECUTE` | After frame execution |
| `BEFORE_LAUNCH` | Before job submission |
| `AFTER_LAUNCH` | After job submission |

### Built-in Shell Modules

PyOutline provides ready-to-use modules for common tasks:

| Module | Description |
|--------|-------------|
| `Shell` | Execute a shell command over a frame range |
| `ShellSequence` | Execute an array of commands, one per frame |
| `ShellCommand` | Execute a single command (always 1 frame) |
| `ShellScript` | Execute an external script file |
| `PyEval` | Execute inline Python code |
