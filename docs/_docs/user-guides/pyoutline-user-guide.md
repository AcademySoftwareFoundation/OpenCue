---
title: "PyOutline User Guide"
nav_order: 47
parent: "User Guides"
layout: default
date: 2026-03-13
description: >
  Comprehensive user guide for building, configuring, and submitting
  OpenCue jobs with PyOutline and pycuerun.
---

# PyOutline User Guide

This guide covers the full capabilities of PyOutline for building and managing OpenCue render jobs.

> **Note:** PyOutline is the job definition library; [pycuerun](/docs/user-guides/pycuerun-user-guide/) is the CLI tool that submits PyOutline jobs to the render farm. You can launch jobs either programmatically via PyOutline's `cuerun.launch()` or from the command line via `pycuerun`.

## Creating Outlines

### Basic Outline

```python
import outline
import outline.modules.shell

ol = outline.Outline("my-job", show="myshow", shot="sh010", user="artist")
```

### Outline Properties

```python
ol.set_frame_range("1-100")
ol.set_env("RENDER_QUALITY", "production")
ol.set_arg("scene_file", "/path/to/scene.ma")
```

### Loading Existing Outlines

```python
# From a Python script
ol = outline.load_outline("/path/to/script.outline")

# From a YAML file
ol = outline.load_outline("/path/to/job.yaml")

# From JSON
ol = outline.load_json('{"name": "test", "range": "1-10", ...}')
```

## Working with Layers

### Shell Module

The most common way to create layers is using the built-in shell modules:

```python
from outline.modules.shell import Shell, ShellSequence, ShellCommand, ShellScript

# Execute a command over a frame range
render = Shell("render", command=["maya", "-render", "-s", "#IFRAME#", "scene.ma"], range="1-100")

# Execute different commands per frame
commands = ["convert img_1.exr img_1.jpg", "convert img_2.exr img_2.jpg"]
convert = ShellSequence("convert", commands=commands)

# Execute a single command (one frame)
cleanup = ShellCommand("cleanup", command=["/bin/rm", "-rf", "/tmp/render_cache"])

# Execute a script file
process = ShellScript("process", script="/path/to/process.sh", range="1-50")
```

### Custom Layers

Create custom layers by subclassing `Layer` and overriding `_execute`:

```python
from outline import Layer

class MyRenderLayer(Layer):
    def __init__(self, name, **args):
        Layer.__init__(self, name, **args)
        self.require_arg("scene_file")

    def _setup(self):
        """Called during outline setup phase."""
        self.put_file(self.get_arg("scene_file"))

    def _execute(self, frames):
        """Called for each frame/chunk during execution."""
        for frame in frames:
            # Your rendering logic here
            pass
```

### Layer Configuration

```python
layer = Shell("render", command=["echo", "#IFRAME#"], range="1-100")

# Set chunk size (frames per task)
layer.set_chunk_size(10)

# Set environment variables
layer.set_env("MAYA_VERSION", "2024")

# Set custom arguments
layer.set_arg("priority", 100)

# Set resource requirements
layer.set_arg("cores", 4)
layer.set_arg("memory", "8g")
```

### Frame Range Tokens

Use these tokens in commands that get replaced at execution time:

| Token | Description |
|-------|-------------|
| `#IFRAME#` | Current frame number |
| `#FRAME_START#` | First frame in range |
| `#FRAME_END#` | Last frame in range |
| `#FRAME_STEP#` | Step between frames |
| `#FRAME_CHUNK#` | Chunk size |

## Dependencies

### Frame-by-Frame

The default dependency type. Each frame in the dependent layer waits for the matching frame:

```python
composite.depend_on(render)
```

### Layer-on-Layer

All frames wait for the entire dependency layer to complete:

```python
publish.depend_all(render)
```

### Previous Frame

Each frame depends on the previous frame in the dependency layer. Useful for simulations:

```python
sim.depend_previous(sim)  # Self-dependency: frame N waits for frame N-1
```

### Any Frame

The dependency is satisfied when any frame in the dependency layer completes:

```python
notify.depend_on(setup, "any")
```

## Pre/Post Processing

### Layer Pre-Process

Runs before the parent layer starts. Outputs are available to the parent:

```python
from outline import LayerPreProcess

class SetupFiles(LayerPreProcess):
    def _execute(self, frames):
        # Download or prepare files
        self.put_data("config", {"resolution": "1920x1080"})

render = Shell("render", command=["echo", "#IFRAME#"], range="1-100")
render.add_child(SetupFiles("setup"))
```

### Layer Post-Process

Runs after the parent layer completes:

```python
from outline import LayerPostProcess

class Cleanup(LayerPostProcess):
    def _execute(self, frames):
        # Clean up temporary files
        pass

render.add_child(Cleanup("cleanup"))
```

### Outline Post-Command

Runs after the entire job completes:

```python
from outline import OutlinePostCommand

class NotifyComplete(OutlinePostCommand):
    def _execute(self, frames):
        # Send notification
        pass

ol.add_layer(NotifyComplete("notify"))
```

## Session Management

Sessions provide persistent storage accessible across frames and layers.

### Storing and Retrieving Files

```python
# Copy a file into the session
layer.put_file("/path/to/input.exr", rename="input")

# Get the session path to a file
path = layer.get_file("input")

# Create a symlink in the session
layer.sym_file("/path/to/large_file.abc")
```

### Storing and Retrieving Data

```python
# Store structured data (serialized as YAML)
layer.put_data("render_config", {
    "resolution": [1920, 1080],
    "samples": 256,
    "output_dir": "/path/to/output"
})

# Retrieve data (in the same or another frame)
config = layer.get_data("render_config")
```

## Launching Jobs

### Programmatic Launch

```python
from outline.cuerun import launch

# Basic launch
jobs = launch(ol)

# With options
jobs = launch(ol,
    pause=True,          # Launch paused
    wait=True,           # Block until complete
    range="1-50",        # Override frame range
    facility="cloud",    # Target facility
    nomail=True,         # Disable email
    maxretries=3,        # Max retries per frame
    os="Linux"           # Target OS
)
```

### Using OutlineLauncher

For more control over the launch process:

```python
from outline.cuerun import OutlineLauncher

launcher = OutlineLauncher(ol)
launcher.set_flag("pause", True)
launcher.set_flag("wait", True)
launcher.set_flag("range", "1-100")

launcher.setup()
jobs = launcher.launch()
```

### Command-Line Launch with pycuerun

```bash
# Basic submission
pycuerun my_script.outline

# With options
pycuerun -f 1-100 -p -w --max-retries 3 my_script.outline

# Execute a specific frame locally
pycuerun -e 5-render my_script.outline

# Inspect without submitting
pycuerun -i my_script.outline
```

## Environment Variables

### Outline-Level Environment

```python
ol = outline.Outline("my-job")
ol.set_env("GLOBAL_SETTING", "value")  # Applied to all layers
```

### Layer-Level Environment

```python
layer.set_env("LAYER_SETTING", "value")  # This layer only
```

### Via pycuerun

```bash
pycuerun --env KEY1=value1 --env KEY2=value2 my_script.outline
```

## Configuration

### Configuration File

PyOutline reads settings from `outline.cfg`:

```ini
[outline]
home = /path/to/pyoutline
session_dir = ~/.opencue/sessions
backend = cue
facility = local
maxretries = 2

[plugin:local]
module = outline.plugins.local
enable = 1
priority = 0
```

### Configuration Search Order

1. `OUTLINE_CONFIG_FILE` environment variable
2. `OL_CONFIG` environment variable (deprecated)
3. `~/.config/opencue/outline.cfg`
4. Built-in defaults

## Local Execution

For development and testing, run jobs locally:

```bash
pycuerun --backend local my_script.outline
```

Or programmatically:

```python
launch(ol, backend="local")
```

The local backend uses SQLite to track frame state and executes frames sequentially, respecting dependencies.
