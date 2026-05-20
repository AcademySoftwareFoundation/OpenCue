---
title: "Configuring PyOutline"
nav_order: 65
parent: "Other Guides"
layout: default
date: 2026-03-13
description: >
  Configure PyOutline settings including backends, sessions, plugins,
  and environment variables for your render pipeline.
---

# Configuring PyOutline

This guide covers all configuration options for PyOutline and pycuerun.

> **Note:** PyOutline is the job definition library and pycuerun is its CLI frontend. Configuration settings in `outline.cfg` affect both — they control backends, session storage, and plugins used by PyOutline when building jobs and by pycuerun when launching them.

## Configuration File

PyOutline uses an INI-style configuration file (`outline.cfg`). The file is loaded from the first location found:

1. Path specified by the `OUTLINE_CONFIG_FILE` environment variable
2. Path specified by the `OL_CONFIG` environment variable (deprecated)
3. `~/.config/opencue/outline.cfg` (user profile)
4. Built-in defaults in the PyOutline package

### Default Configuration

```ini
[outline]
home = /path/to/pyoutline
session_dir = ~/.opencue/sessions
wrapper_dir = /path/to/wrappers
backend = cue
facility = local
maxretries = 2
spec_version = 1.0
```

### Configuration Options

| Setting | Description | Default |
|---------|-------------|---------|
| `home` | PyOutline installation root | Package directory |
| `session_dir` | Session storage location | `~/.opencue/sessions` |
| `wrapper_dir` | Shell wrapper scripts | Package wrappers directory |
| `bin_dir` | Binary directory for pycuerun | Package bin directory |
| `backend` | Default backend (`cue` or `local`) | `cue` |
| `facility` | Default facility | `local` |
| `maxretries` | Default max retries per frame | `2` |
| `spec_version` | OpenCue job spec version | `1.0` |
| `user_dir` | User-specific directory | Platform-dependent |

## Plugin Configuration

Register plugins in the configuration file:

```ini
[plugin:local]
module = outline.plugins.local
enable = 1
priority = 0

[plugin:custom_plugin]
module = my_studio.outline_plugins.custom
enable = 1
priority = 10
```

### Plugin Settings

| Setting | Description |
|---------|-------------|
| `module` | Python module path for the plugin |
| `enable` | Enable (`1`) or disable (`0`) the plugin |
| `priority` | Load order priority (lower loads first) |

## Environment Variables

### Core Variables

| Variable | Description |
|----------|-------------|
| `OUTLINE_CONFIG_FILE` | Path to custom configuration file |
| `CUEBOT_HOSTS` | Cuebot server hostnames (comma-separated) |
| `SHOW` | Default show name |
| `SHOT` | Default shot name |
| `USER` | Override username |
| `FR` | Default frame range for pycuerun |
| `FACILITY` / `RENDER_TO` | Default render facility |

### Execution Variables

| Variable | Description |
|----------|-------------|
| `OL_VERSION` | PyOutline version to use |
| `OL_OS` | Target operating system |
| `OL_TAG_OVERRIDE` | Override layer tags |
| `OL_LAYER_RANGE` | Per-layer frame range (set during execution) |

### Module Loading

| Variable | Description |
|----------|-------------|
| `CUE_MODULE_PATHS` | Additional paths to search for outline modules (colon-separated) |

## Session Configuration

Sessions store runtime data for job execution. By default, sessions are created at:

```
~/.opencue/sessions/<show-shot-user_name>/<uuid>/
```

### Session Directory Structure

```
session_root/
├── outline.yaml          # Serialized outline
├── layer1/               # Per-layer storage
│   ├── files/            # Copied files
│   └── data/             # Serialized data
├── layer2/
│   ├── files/
│   └── data/
└── ...
```

### Customizing Session Location

```ini
[outline]
session_dir = /shared/render/sessions
```

Or via environment:

```bash
export OUTLINE_CONFIG_FILE=/path/to/custom/outline.cfg
```

## Backend Configuration

### OpenCue Backend

The default backend submits jobs to Cuebot. Configure the Cuebot connection:

```bash
export CUEBOT_HOSTS="cuebot1.example.com,cuebot2.example.com"
```

### Local Backend

The local backend executes frames on the local machine. Useful for development:

```bash
pycuerun --backend local my_script.outline
```

The local backend uses SQLite for frame state tracking and executes frames sequentially in dependency order.

## Writing Custom Plugins

Create a plugin module with the following interface:

```python
def loaded():
    """Called when the plugin is first loaded."""
    pass

def init(layer):
    """Called when a layer is initialized."""
    # Add event listeners, modify layer behavior, etc.
    pass

def init_cuerun_plugin(cuerun_parser):
    """Called to add custom CLI options to pycuerun."""
    cuerun_parser.add_option("--my-option", help="Custom option")
```

Register the plugin in `outline.cfg`:

```ini
[plugin:my_plugin]
module = my_studio.plugins.my_plugin
enable = 1
```
