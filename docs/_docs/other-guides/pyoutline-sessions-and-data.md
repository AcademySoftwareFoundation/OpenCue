---
title: "PyOutline Sessions and Data Exchange"
nav_order: 67
parent: "Other Guides"
layout: default
date: 2026-03-13
description: >
  How to use PyOutline sessions for persistent storage and data exchange
  between frames and layers in OpenCue jobs.
---

# PyOutline Sessions and Data Exchange

This guide explains how to use PyOutline's session system for sharing files and data between frames and layers.

> **Note:** Sessions are created by PyOutline (the job definition library) during job setup and accessed during frame execution by pycuerun (the CLI tool). PyOutline defines the session API; pycuerun invokes it when executing frames on render hosts.

## What is a Session?

A session is a persistent directory structure created for each job submission. It provides a shared filesystem space where frames and layers can store and retrieve files and structured data.

Sessions are created automatically during the outline setup phase and persist for the lifetime of the job.

## Session Location

Sessions are stored at:

```
~/.opencue/sessions/<show-shot-user_name>/<uuid>/
```

Each session has a unique identifier and an organized directory structure for each layer.

## File Operations

### Copying Files into a Session

Use `put_file()` to copy a file into the session directory:

```python
# Copy with original filename
layer.put_file("/path/to/scene.ma")

# Copy with a custom name
layer.put_file("/path/to/scene.ma", rename="main_scene")
```

### Retrieving Files

```python
# Get the session path to a stored file
path = layer.get_file("main_scene")
# Returns: ~/.opencue/sessions/.../layer_name/main_scene
```

### Creating Symlinks

For large files, create symlinks instead of copies:

```python
layer.sym_file("/path/to/large_cache.abc")
```

### Making Directories

```python
from outline.io import Path

p = Path("/path/in/session")
p.mkdir()
```

## Data Exchange

### Storing Data

Use `put_data()` to serialize Python data (stored as YAML):

```python
layer.put_data("render_settings", {
    "resolution": [1920, 1080],
    "samples": 256,
    "engine": "arnold",
    "aovs": ["beauty", "depth", "normal"]
})
```

### Retrieving Data

```python
settings = layer.get_data("render_settings")
print(settings["resolution"])  # [1920, 1080]
```

## Cross-Layer Data Exchange

Data stored by one layer can be accessed by another layer, enabling pipeline workflows.

### Example: Render-Composite Pipeline

```python
from outline import Layer, Outline
from outline.modules.shell import Shell

class RenderLayer(Layer):
    def _execute(self, frames):
        for frame in frames:
            output = f"/renders/frame_{frame:04d}.exr"
            # Simulate render and record output
            self.put_data(f"output_{frame}", {"path": output, "status": "complete"})

class CompositeLayer(Layer):
    def _execute(self, frames):
        for frame in frames:
            render = self.get_outline().get_layer("render")
            data = render.get_data(f"output_{frame}")
            # Use the render output path
            print(f"Compositing: {data['path']}")

ol = Outline("pipeline-job")
render = RenderLayer("render", range="1-10")
composite = CompositeLayer("composite", range="1-10")
composite.depend_on(render)

ol.add_layer(render)
ol.add_layer(composite)
```

### Pre-Process Data Handoff

LayerPreProcess stores outputs that the parent layer can access:

```python
from outline import LayerPreProcess

class PrepareScene(LayerPreProcess):
    def _execute(self, frames):
        # Download or prepare scene files
        scene_path = "/path/to/prepared/scene.ma"
        self.put_data("scene_config", {"path": scene_path, "ready": True})

class RenderLayer(Layer):
    def _execute(self, frames):
        config = self.get_child("prepare").get_data("scene_config")
        # Use config["path"] for rendering

render = RenderLayer("render", range="1-100")
render.add_child(PrepareScene("prepare"))
```

## Session Lifecycle

1. **Creation**: Session directory is created during `outline.setup()`
2. **Population**: Files and data are stored during setup and execution
3. **Access**: Frames read stored files and data during execution
4. **Persistence**: Sessions remain on disk after job completion for debugging

## Best Practices

- Use `put_data()` for structured configuration and metadata
- Use `put_file()` for input files needed by frames
- Use `sym_file()` for large files to avoid unnecessary copies
- Use layer-specific namespaces in data keys to avoid collisions
- Clean up session data after jobs complete if disk space is a concern
