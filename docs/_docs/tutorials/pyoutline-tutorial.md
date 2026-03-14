---
title: "PyOutline Tutorial"
nav_order: 88
parent: Tutorials
layout: default
date: 2026-03-13
description: >
  A hands-on tutorial for building OpenCue render jobs with PyOutline,
  covering basic jobs, multi-layer pipelines, dependencies, and custom layers.
---

# PyOutline Tutorial

This tutorial walks you through building increasingly complex OpenCue jobs with PyOutline and pycuerun.

> **Note:** PyOutline is the Python library for defining jobs; pycuerun is the CLI tool for launching them. This tutorial covers both — you'll use PyOutline's API to build jobs and pycuerun to submit them from the command line. See also the [PyCuerun Tutorial](/docs/tutorials/pycuerun-tutorial/).

## What You'll Learn

- Creating basic single-layer jobs
- Building multi-layer render pipelines
- Configuring dependencies between layers
- Writing custom layer classes
- Using sessions for data exchange
- Pre/post processing with child layers
- Debugging jobs with local execution

## Prerequisites

- OpenCue environment running with at least one RQD host
- PyCue and PyOutline installed (`pip install opencue-pycue opencue-pyoutline`)
- `CUEBOT_HOSTS` environment variable set

## Tutorial 1: Your First Job

Create `tutorial_01.py`:

```python
import outline
import outline.modules.shell

# Create the outline (job definition)
ol = outline.Outline("tutorial-01", show="testing", shot="test")

# Create a shell layer that runs over 10 frames
layer = outline.modules.shell.Shell(
    "hello",
    command=["echo", "Hello from frame #IFRAME#"],
    range="1-10"
)

# Add the layer to the outline
ol.add_layer(layer)

# Launch the job
outline.cuerun.launch(ol, use_pycuerun=False, os="Linux")
print("Job submitted!")
```

Run it:

```bash
python tutorial_01.py
```

This creates a job with 10 frames, each executing `echo Hello from frame N`.

## Tutorial 2: Multi-Layer Pipeline

Create `tutorial_02.py`:

```python
import outline
import outline.modules.shell

ol = outline.Outline("tutorial-02-pipeline", show="testing", shot="test")

# Layer 1: Render
render = outline.modules.shell.Shell(
    "render",
    command=["echo", "Rendering frame #IFRAME#"],
    range="1-20"
)
ol.add_layer(render)

# Layer 2: Composite (depends on render)
composite = outline.modules.shell.Shell(
    "composite",
    command=["echo", "Compositing frame #IFRAME#"],
    range="1-20"
)
composite.depend_on(render)  # Frame-by-frame dependency
ol.add_layer(composite)

# Layer 3: Publish (depends on all composite frames)
publish = outline.modules.shell.Shell(
    "publish",
    command=["echo", "Publishing frame #IFRAME#"],
    range="1-20"
)
publish.depend_all(composite)  # Layer-on-layer dependency
ol.add_layer(publish)

outline.cuerun.launch(ol, use_pycuerun=False)
```

This creates a three-stage pipeline:
- `render`: All frames can run in parallel
- `composite`: Each frame waits for the corresponding render frame
- `publish`: No frame runs until all composite frames finish

## Tutorial 3: Using Chunking

Create `tutorial_03.py`:

```python
import outline
import outline.modules.shell

ol = outline.Outline("tutorial-03-chunking", show="testing", shot="test")

# Process 100 frames in chunks of 10 (creates 10 tasks)
layer = outline.modules.shell.Shell(
    "batch-process",
    command=["echo", "Processing frame #IFRAME#"],
    range="1-100"
)
layer.set_chunk_size(10)
ol.add_layer(layer)

outline.cuerun.launch(ol, use_pycuerun=False)
print("Submitted 100 frames in 10 chunks of 10")
```

Chunking is useful when your application has significant startup overhead. Each task processes multiple frames, reducing total overhead.

## Tutorial 4: Custom Layer Classes

Create `tutorial_04.py`:

```python
import os
import outline
from outline import Layer

class FileCounter(Layer):
    """A custom layer that counts files in a directory."""

    def __init__(self, name, **args):
        Layer.__init__(self, name, **args)
        self.require_arg("directory")

    def _setup(self):
        """Validate the directory exists during setup."""
        directory = self.get_arg("directory")
        if not os.path.isdir(directory):
            raise outline.LayerException(f"Directory not found: {directory}")

    def _execute(self, frames):
        """Execute for each frame/chunk."""
        directory = self.get_arg("directory")
        files = os.listdir(directory)
        count = len(files)
        print(f"Found {count} files in {directory}")

        # Store the result for other layers to access
        self.put_data("file_count", {"directory": directory, "count": count})


ol = outline.Outline("tutorial-04-custom", show="testing", shot="test")

counter = FileCounter(
    "count-files",
    directory="/tmp",
    range="1"
)
ol.add_layer(counter)

outline.cuerun.launch(ol)
```

Custom layers override `_execute()` for the main logic and optionally `_setup()` for validation.

## Tutorial 5: Data Exchange Between Layers

Create `tutorial_05.py`:

```python
import json
import outline
from outline import Layer

class Producer(Layer):
    """Produces data for downstream layers."""

    def _execute(self, frames):
        for frame in frames:
            result = {
                "frame": frame,
                "output": f"/renders/frame_{frame:04d}.exr",
                "status": "complete"
            }
            self.put_data(f"frame_{frame}", result)
            print(f"Produced data for frame {frame}")


class Consumer(Layer):
    """Consumes data from the producer layer."""

    def _execute(self, frames):
        producer = self.get_outline().get_layer("producer")
        for frame in frames:
            data = producer.get_data(f"frame_{frame}")
            print(f"Consuming frame {frame}: {data['output']}")


ol = outline.Outline("tutorial-05-data", show="testing", shot="test")

producer = Producer("producer", range="1-5")
consumer = Consumer("consumer", range="1-5")
consumer.depend_on(producer)

ol.add_layer(producer)
ol.add_layer(consumer)

outline.cuerun.launch(ol)
```

Sessions automatically serialize data as YAML, so you can exchange complex Python objects between frames.

## Tutorial 6: Pre and Post Processing

Create `tutorial_06.py`:

```python
import outline
from outline import Layer, LayerPreProcess, LayerPostProcess, OutlinePostCommand
from outline.modules.shell import Shell

class SetupScene(LayerPreProcess):
    """Downloads and prepares scene files before rendering."""

    def _execute(self, frames):
        print("Setting up scene files...")
        self.put_data("scene_ready", {"path": "/scenes/main.ma", "ready": True})


class VerifyOutput(LayerPostProcess):
    """Verifies render outputs after layer completion."""

    def _execute(self, frames):
        print("Verifying render outputs...")


class NotifyTeam(OutlinePostCommand):
    """Sends notification after the entire job completes."""

    def _execute(self, frames):
        print("Job complete! Notifying team...")


ol = outline.Outline("tutorial-06-hooks", show="testing", shot="test")

# Main render layer with pre/post processing
render = Shell("render", command=["echo", "Rendering #IFRAME#"], range="1-10")
render.add_child(SetupScene("setup-scene"))
render.add_child(VerifyOutput("verify"))

ol.add_layer(render)

# Post-job notification
ol.add_layer(NotifyTeam("notify"))

outline.cuerun.launch(ol, use_pycuerun=False)
```

Child layers run automatically:
- `SetupScene` (PreProcess) runs before any render frame starts
- `VerifyOutput` (PostProcess) runs after all render frames complete
- `NotifyTeam` (PostCommand) runs after the entire job completes

## Tutorial 7: Outline Scripts with pycuerun

Instead of Python scripts with explicit launch calls, you can write outline scripts that pycuerun loads.

Create `tutorial_07.outline`:

```python
import outline.modules.shell

# Layers are automatically added to the current outline
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

Launch with pycuerun:

```bash
# Basic launch
pycuerun tutorial_07.outline

# Override frame range
pycuerun -f 1-50 tutorial_07.outline

# Launch paused
pycuerun -p tutorial_07.outline

# Inspect without launching
pycuerun -i tutorial_07.outline
```

## Tutorial 8: Local Debugging

Debug a failing frame by running it locally:

```bash
# Step 1: Inspect the outline
pycuerun -i tutorial_07.outline

# Step 2: Execute frame 5 of the render layer locally
pycuerun -e 5-render tutorial_07.outline

# Step 3: Run with debug logging
pycuerun -D -e 5-render tutorial_07.outline
```

For full local execution of all frames:

```bash
pycuerun --backend local tutorial_07.outline
```

The local backend runs frames sequentially on your machine, respecting dependencies.

## Tutorial 9: Environment Variables and Configuration

Create `tutorial_09.outline`:

```python
import os
import outline
import outline.modules.shell

# Get the current outline
ol = outline.current_outline()

# Set job-wide environment variables
ol.set_env("RENDER_QUALITY", "preview")
ol.set_env("OUTPUT_DIR", "/renders/preview")

# Create a layer with its own environment
render = outline.modules.shell.Shell(
    "render",
    command=["echo", "Quality: $RENDER_QUALITY, Engine: $RENDER_ENGINE"],
    range="1-10"
)
render.set_env("RENDER_ENGINE", "arnold")

# Another layer inherits job env but not render's layer env
preview = outline.modules.shell.Shell(
    "preview",
    command=["echo", "Quality: $RENDER_QUALITY"],
    range="1-10"
)
preview.depend_all(render)
```

Launch with additional environment variables:

```bash
pycuerun --env RENDER_QUALITY=production --env OUTPUT_DIR=/renders/final tutorial_09.outline
```

## Tutorial 10: Simulation Dependencies

Create `tutorial_10.py`:

```python
import outline
from outline.modules.shell import Shell

ol = outline.Outline("tutorial-10-simulation", show="testing", shot="test")

# Simulation layer where each frame depends on the previous frame
sim = Shell(
    "fluid-sim",
    command=["echo", "Simulating frame #IFRAME#"],
    range="1-100"
)

# Frame N waits for frame N-1 (sequential execution)
sim.depend_previous(sim)
ol.add_layer(sim)

# Render can process frames as they become available
render = Shell(
    "render-sim",
    command=["echo", "Rendering sim frame #IFRAME#"],
    range="1-100"
)
render.depend_on(sim)  # Frame-by-frame
ol.add_layer(render)

outline.cuerun.launch(ol, use_pycuerun=False)
```

The `depend_previous` creates a chain: frame 1 runs first, then frame 2, then frame 3, etc. The render layer can start processing frames as soon as the corresponding simulation frame completes.

## Summary

| Tutorial | Concept |
|----------|---------|
| 1 | Basic job creation and submission |
| 2 | Multi-layer pipelines with dependencies |
| 3 | Frame chunking for efficiency |
| 4 | Custom layer classes |
| 5 | Data exchange via sessions |
| 6 | Pre/post processing hooks |
| 7 | Outline scripts with pycuerun |
| 8 | Local debugging |
| 9 | Environment variables |
| 10 | Simulation dependencies |
