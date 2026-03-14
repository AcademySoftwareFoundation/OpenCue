---
title: "PyOutline and PyCuerun Development Guide"
nav_order: 108
parent: "Developer Guide"
layout: default
date: 2026-03-13
description: >
  Technical documentation for developers contributing to PyOutline and pycuerun,
  including architecture, module development, plugin creation, and testing.
---

# PyOutline and PyCuerun Development Guide

This guide provides technical documentation for developers contributing to PyOutline and pycuerun.

> **Note:** PyOutline is the job definition library and pycuerun is its CLI frontend. PyOutline defines outlines, layers, and sessions; pycuerun parses outline scripts, submits them to Cuebot, and executes frames on render hosts. Both live in the `pyoutline/` package. See also the [PyCuerun Development Guide](/docs/developer-guide/pycuerun-development/).

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Development Setup](#development-setup)
4. [Code Organization](#code-organization)
5. [Creating Custom Modules](#creating-custom-modules)
6. [Writing Plugins](#writing-plugins)
7. [Backend Development](#backend-development)
8. [Testing](#testing)
9. [Key Design Patterns](#key-design-patterns)
10. [Troubleshooting](#troubleshooting)

## Overview

PyOutline is the job specification library for OpenCue. It provides:
- A Python API for constructing job definitions
- Serialization to OpenCue job specification format
- Pluggable backends for job execution
- A plugin system for extending behavior
- Session management for runtime data exchange

PyCuerun is the command-line frontend that:
- Parses outline scripts
- Manages launch options
- Executes individual frames on render hosts
- Provides development and debugging tools

### Key Technologies

- **Python 3.7+** with type hints
- **PyYAML** for serialization
- **FileSequence** for frame range parsing
- **PyCue (opencue)** for Cuebot API communication
- **SQLite** for local backend state management
- **Pytest** for testing

## Architecture

### High-Level Architecture

```
┌──────────────────────────────────────────────┐
│                   pycuerun                    │
│         (CLI / Frame Executor)                │
├──────────────────────────────────────────────┤
│              OutlineLauncher                  │
│     (Setup, Serialization, Launch)            │
├──────────────┬───────────────────────────────┤
│   Outline    │         Session               │
│  (Job Def)   │    (Persistent Storage)        │
├──────────────┤                               │
│   Layers     │                               │
│  (Tasks)     │                               │
├──────────────┴───────────────────────────────┤
│              Backend (pluggable)              │
│         ┌──────────┬──────────┐              │
│         │   cue    │  local   │              │
│         │ (Cuebot) │ (SQLite) │              │
│         └──────────┴──────────┘              │
├──────────────────────────────────────────────┤
│           Plugin Manager                      │
│     (Extensions & Event Hooks)                │
└──────────────────────────────────────────────┘
```

### Outline Lifecycle

```
INIT (mode=0)                SETUP (mode=1)              READY (mode=2)
  Parse script ──────────>  Create session ──────────>  Serialize
  Add layers                 Stage files                  Submit to backend
  Set properties             Validate args
  Register deps              Run layer._setup()
```

### Layer Metaclass System

The `LayerType` metaclass intercepts layer construction to:
1. Automatically register layers with the current outline
2. Initialize plugins on the layer
3. Fire `AFTER_INIT` events

```python
class LayerType(type):
    def __call__(cls, *args, **kwargs):
        layer = super().__call__(*args, **kwargs)
        # Auto-register with current outline
        outline = current_outline()
        if outline:
            outline.add_layer(layer)
        # Initialize plugins
        PluginManager.init_plugin_all(layer)
        return layer
```

## Development Setup

### Clone and Install

```bash
git clone https://github.com/AcademySoftwareFoundation/OpenCue.git
cd OpenCue

# Install in development mode
pip install -e pycue/
pip install -e pyoutline/
```

### Run Tests

```bash
cd pyoutline
python -m pytest tests/ -v
```

### Run a Specific Test

```bash
python -m pytest tests/test_layer.py -v
python -m pytest tests/test_layer.py::LayerTest::test_chunk_size -v
```

## Code Organization

```
pyoutline/
├── bin/
│   ├── pycuerun              # CLI entry point
│   ├── cuerunbase.py         # Abstract base for cuerun tools
│   └── util_qc_job_layer.py  # QC integration utility
├── outline/
│   ├── __init__.py           # Package exports
│   ├── loader.py             # Outline class, script loading
│   ├── layer.py              # Layer, Frame, Pre/PostProcess
│   ├── session.py            # Session storage
│   ├── cuerun.py             # OutlineLauncher, launch helpers
│   ├── config.py             # Configuration management
│   ├── constants.py          # Enums and constants
│   ├── depend.py             # Dependency types
│   ├── event.py              # Event system
│   ├── exception.py          # Exception hierarchy
│   ├── executor.py           # Thread pool
│   ├── io.py                 # File I/O, FileSpec
│   ├── util.py               # Frame set utilities
│   ├── outline.cfg           # Default configuration
│   ├── backend/
│   │   ├── cue.py            # OpenCue backend
│   │   └── local.py          # Local execution backend
│   ├── modules/
│   │   ├── __init__.py
│   │   └── shell.py          # Shell command modules
│   └── plugins/
│       ├── manager.py        # Plugin manager
│       └── local.py          # Local cores plugin
├── tests/
│   ├── test_layer.py
│   ├── test_loader.py
│   ├── test_session.py
│   ├── test_depend.py
│   ├── test_config.py
│   ├── test_executor.py
│   ├── test_json.py
│   ├── test_utils.py
│   ├── backend/
│   │   ├── test_cue.py
│   │   └── test_local.py
│   ├── modules/
│   │   └── test_shell.py
│   └── scripts/             # Test outline scripts
└── pyproject.toml
```

## Creating Custom Modules

Custom modules extend `Layer` to provide reusable task types.

### Basic Module

```python
from outline import Layer

class MyRenderer(Layer):
    """Custom renderer module."""

    def __init__(self, name, **args):
        Layer.__init__(self, name, **args)
        # Declare required arguments
        self.require_arg("scene_file")
        self.require_arg("output_dir")
        # Set defaults
        self.set_arg("quality", args.get("quality", "production"))

    def _setup(self):
        """Called during outline setup. Validate inputs and stage files."""
        scene = self.get_arg("scene_file")
        self.put_file(scene, rename="scene")

    def _execute(self, frames):
        """Called for each frame/chunk on the render host."""
        scene = self.get_file("scene")
        output_dir = self.get_arg("output_dir")
        quality = self.get_arg("quality")

        for frame in frames:
            # Your rendering logic here
            print(f"Rendering frame {frame} with {quality} quality")

    def _before_execute(self):
        """Called before _execute. Set up per-frame state."""
        pass

    def _after_execute(self):
        """Called after _execute. Clean up per-frame state."""
        pass
```

### Registering Modules via Environment

Use the `CUE_MODULE_PATHS` environment variable to make custom modules discoverable:

```bash
export CUE_MODULE_PATHS="/path/to/my/modules:/path/to/more/modules"
```

## Writing Plugins

Plugins extend PyOutline behavior without modifying core code.

### Plugin Interface

```python
"""my_plugin.py - Example PyOutline plugin."""

def loaded():
    """Called once when the plugin module is first loaded."""
    print("My plugin loaded")

def init(layer):
    """Called for every layer after construction.

    Use this to add event listeners, modify layer defaults,
    or inject behavior.
    """
    # Example: Add a default environment variable to all layers
    layer.set_env("PLUGIN_ACTIVE", "1")

    # Example: Listen for events
    from outline.event import LayerEvent
    layer.add_event_listener(
        LayerEvent.BEFORE_EXECUTE,
        lambda event: print(f"About to execute {event.layer.get_name()}")
    )

def init_cuerun_plugin(parser):
    """Called to add custom options to the pycuerun CLI.

    Args:
        parser: CuerunOptionParser instance
    """
    parser.add_option(
        "--my-flag",
        action="store_true",
        default=False,
        help="Enable my custom feature"
    )
```

### Registering Plugins

Add to `outline.cfg`:

```ini
[plugin:my_plugin]
module = my_studio.plugins.my_plugin
enable = 1
priority = 0
```

## Backend Development

Create custom backends for alternative execution environments.

### Backend Interface

A backend module must implement:

```python
def launch(launcher, use_pycuerun=True):
    """Submit the outline for execution.

    Args:
        launcher: OutlineLauncher instance
        use_pycuerun: Whether to wrap commands with pycuerun

    Returns:
        List of launched job objects
    """
    pass

def serialize(launcher):
    """Convert the outline to a job specification.

    Args:
        launcher: OutlineLauncher instance

    Returns:
        Job specification (format depends on backend)
    """
    pass

def build_command(launcher_or_outline, layer):
    """Build the command string for a layer.

    Returns:
        List of command arguments
    """
    pass
```

### OpenCue Backend Flow

```
serialize(launcher)
  → Build XML job spec
  → Set facility, show, shot, user
  → For each layer:
    → Build pycuerun wrapper command
    → Set frame range, tags, dependencies
  → Return XML string

launch(launcher)
  → serialize(launcher)
  → opencue.api.launchSpecAndWait(spec)
  → Return [job]
```

### Local Backend Flow

```
launch(launcher)
  → Create SQLite database
  → Insert all frames with state WAITING
  → Dispatcher loop:
    → Find frames with satisfied dependencies
    → Execute frame via subprocess
    → Update state (RUNNING → DONE/DEAD)
```

## Testing

### Test Structure

Tests are organized to mirror the source structure:

```
tests/
├── test_layer.py        # Layer, Frame, Pre/PostProcess
├── test_loader.py       # Outline loading and parsing
├── test_session.py      # Session file/data operations
├── test_depend.py       # Dependency creation and types
├── test_config.py       # Configuration loading
├── backend/
│   ├── test_cue.py      # OpenCue backend serialization
│   └── test_local.py    # Local backend execution
└── modules/
    └── test_shell.py    # Shell module variants
```

### Writing Tests

```python
import unittest
from unittest import mock
import outline
from outline.modules.shell import Shell

class MyModuleTest(unittest.TestCase):

    def setUp(self):
        """Create a fresh outline for each test."""
        self.ol = outline.Outline(
            "test-job",
            frame_range="1-10",
            show="testing",
            shot="test"
        )

    def test_layer_creation(self):
        layer = Shell("test", command=["echo", "#IFRAME#"], range="1-10")
        self.ol.add_layer(layer)
        self.assertEqual(layer.get_name(), "test")
        self.assertEqual(layer.get_frame_range(), "1-10")

    def test_dependencies(self):
        layer1 = Shell("layer1", command=["echo", "1"], range="1-10")
        layer2 = Shell("layer2", command=["echo", "2"], range="1-10")
        layer2.depend_on(layer1)
        self.ol.add_layer(layer1)
        self.ol.add_layer(layer2)
        self.assertEqual(len(layer2.get_depends()), 1)

    @mock.patch("opencue.api.launchSpecAndWait")
    def test_launch(self, mock_launch):
        layer = Shell("test", command=["echo", "#IFRAME#"], range="1-10")
        self.ol.add_layer(layer)
        outline.cuerun.launch(self.ol, use_pycuerun=False)
        mock_launch.assert_called_once()
```

### Running Tests

```bash
# All tests
cd pyoutline && python -m pytest tests/ -v

# Specific module
python -m pytest tests/test_layer.py -v

# With coverage
python -m pytest tests/ --cov=outline --cov-report=html
```

## Key Design Patterns

### Singleton Outline

During script parsing, `current_outline()` returns the active outline context. The `LayerType` metaclass uses this to auto-register layers:

```python
# In an outline script, layers auto-register:
Shell("my-layer", command=["echo", "hi"], range="1-10")
# Equivalent to:
# ol = current_outline()
# ol.add_layer(Shell(...))
```

### Required Arguments

Use `require_arg()` in `__init__` to enforce layer configuration:

```python
def __init__(self, name, **args):
    Layer.__init__(self, name, **args)
    self.require_arg("scene_file")           # Any type
    self.require_arg("quality", str)          # Must be string
    self.require_arg("samples", int)          # Must be int
```

### Frame Token Substitution

The `#IFRAME#` token in commands is replaced with the actual frame number at execution time. This happens in the backend's command builder.

### YAML Serialization

Outlines and their components support YAML serialization for session persistence. Custom YAML constructors and representers are registered for types like `FileSpec`.

## Troubleshooting

### Common Issues

**Layer not found during execution:**
Layer names are case-sensitive and must match exactly between `depend_on()` calls and layer construction.

**Session data not available:**
Ensure dependencies are set correctly. Data stored by layer A is only guaranteed available to layer B if B depends on A.

**Configuration not loading:**
Check the config file search order: `$OUTLINE_CONFIG_FILE` → `~/.config/opencue/outline.cfg` → built-in defaults.

**Plugin not loading:**
Verify the plugin is registered in `outline.cfg` with `enable = 1` and the module path is importable.

### Debug Techniques

1. **Inspect outlines:** `pycuerun -i script.outline`
2. **Local execution:** `pycuerun --backend local script.outline`
3. **Single frame debug:** `pycuerun -D -e 1-layer_name script.outline`
4. **Check serialization:** Use `OutlineLauncher.serialize()` to inspect the generated job spec
