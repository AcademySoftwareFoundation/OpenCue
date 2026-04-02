---
title: "PyCuerun Development Guide"
nav_order: 109
parent: "Developer Guide"
layout: default
date: 2026-03-13
description: >
  Technical documentation for developers contributing to pycuerun, including
  architecture, CLI extension, testing, and the frame execution pipeline.
---

# PyCuerun Development Guide

This guide provides technical documentation for developers contributing to pycuerun.

> **Note:** PyCuerun is the command-line frontend for [PyOutline](/docs/developer-guide/pyoutline-development/), the job definition library. PyOutline provides the `Outline`, `Layer`, and `Session` classes; pycuerun wraps them with CLI argument parsing, job submission, and frame execution. Both are part of the `pyoutline/` package.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Development Setup](#development-setup)
4. [Code Organization](#code-organization)
5. [Execution Modes](#execution-modes)
6. [CLI Option System](#cli-option-system)
7. [Job Serialization Pipeline](#job-serialization-pipeline)
8. [QC Integration](#qc-integration)
9. [Extending PyCuerun](#extending-pycuerun)
10. [Testing](#testing)
11. [Troubleshooting](#troubleshooting)

## Overview

PyCuerun is the command-line frontend for PyOutline. It serves two roles:

1. **Job launcher**: Parses outline scripts and submits them to the OpenCue render farm
2. **Frame executor**: Executes individual frames on render hosts when invoked by Cuebot

### Design Goals

- **Dual-role simplicity**: A single binary handles both submission and execution
- **Extensibility**: Plugin system for adding CLI options and behavior
- **Legacy compatibility**: Automatic conversion of olrun arguments
- **Version management**: Support for pinning and overriding PyOutline versions

### Key Technologies

- **Python 3.7+** with type hints
- **OptionParser** for CLI argument parsing (via `CuerunOptionParser`)
- **PyOutline** for job specification and session management
- **PyCue (opencue)** for Cuebot API communication
- **XML ElementTree** for job spec serialization

## Architecture

### High-Level Flow

```text
pycuerun [options] script.outline [frame_range]
         │
         ▼
┌─────────────────────┐
│     PyCuerun        │  bin/pycuerun
│  (AbstractCuerun)   │
└────────┬────────────┘
         │
         ├── convert_sys_args_from_olrun()   # Legacy arg translation
         │
         ▼
┌─────────────────────┐
│  handle_core_args() │  bin/cuerunbase.py
│  (version, repos,   │
│   debug, verbose)   │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│ CuerunOptionParser  │  outline/cuerun.py
│  parse_args()       │
│  Standard + Dev +   │
│  Job + Plugin opts  │
└────────┬────────────┘
         │
         ▼
┌─────────────────────────────────────────────┐
│          handle_my_options()                 │
│                                             │
│  ┌──────────┐  ┌──────────┐  ┌───────────┐ │
│  │ -e frame │  │ -i       │  │ (default) │ │
│  │ execute  │  │ inspect  │  │  launch   │ │
│  └────┬─────┘  └────┬─────┘  └─────┬─────┘ │
│       │              │              │       │
│       ▼              ▼              ▼       │
│  execute_frame  inspect_script  launch_outline
└─────────────────────────────────────────────┘
```

### Component Relationships

```text
bin/pycuerun                   CLI entry point, PyCuerun class
    │
    ├── bin/cuerunbase.py      AbstractCuerun base class, version setup
    │
    ├── outline/cuerun.py      OutlineLauncher, CuerunOptionParser, launch()
    │       │
    │       ├── outline/loader.py      load_outline(), parse scripts
    │       │
    │       └── outline/backend/
    │               ├── cue.py         OpenCue submission, XML serialization
    │               └── local.py       Local SQLite-based execution
    │
    └── bin/util_qc_job_layer.py   QC hold utility (pauses job for artist review)
```

### Class Hierarchy

```text
AbstractCuerun (cuerunbase.py)
│   - handle_core_arguments()     # Version, debug, verbose
│   - __setup_parser()            # Creates CuerunOptionParser
│   - add_my_options()            # Override point for subclasses
│   - handle_my_options()         # Override point for subclasses
│   - launch_outline()            # Emit events, delegate to cuerun.launch()
│   - go()                        # Main entry: parse → handle_standard → handle_my
│
└── PyCuerun (bin/pycuerun)
        - add_my_options()        # Frame execution, inspect, QC options
        - handle_my_options()     # Route to execute/inspect/launch

OptionParser
│
└── CuerunOptionParser (outline/cuerun.py)
        - Standard options         (-b, -s, -F, -V, -D)
        - Development options      (-v, -r, --dev, --env)
        - Job options              (-p, -w, -t, -f, --shot, --os, ...)
        - Plugin options           (dynamically added by plugins)
        - add_plugin_option()      # Plugins call this to register options
        - options_to_args()        # Convert parsed options to dict
        - setup_frame_range()      # Resolve range from args or $FR
```

## Development Setup

### Prerequisites

- Python 3.7+
- OpenCue repository cloned

### Install in Development Mode

```bash
cd OpenCue

python3 -m venv venv
source venv/bin/activate

pip install -e pycue/
pip install -e pyoutline/
```

Verify:

```bash
pycuerun --help
```

## Code Organization

```text
pyoutline/
├── bin/
│   ├── pycuerun                  # Main CLI entry point
│   │                             #   PyCuerun(AbstractCuerun)
│   │                             #   convert_sys_args_from_olrun()
│   │                             #   inspect_script()
│   │
│   ├── cuerunbase.py             # Abstract base class
│   │                             #   AbstractCuerun
│   │                             #   handle_core_arguments()
│   │                             #   setup_outline_environment()
│   │                             #   signal_handler()
│   │
│   └── util_qc_job_layer.py      # QC hold: pauses job, adds comment
│
├── outline/
│   ├── cuerun.py                 # OutlineLauncher, CuerunOptionParser
│   │                             #   launch(), execute_frame()
│   │                             #   get_launch_facility()
│   │                             #   import_backend_module()
│   │
│   ├── backend/
│   │   ├── cue.py                # OpenCue backend
│   │   │                         #   build_command() — wraps with pycuerun
│   │   │                         #   serialize() / _serialize()
│   │   │                         #   launch(), wait(), test()
│   │   │                         #   build_dependencies()
│   │   │
│   │   └── local.py              # Local backend
│   │                             #   Dispatcher (SQLite-based)
│   │                             #   build_command()
│   │
│   └── plugins/
│       └── local.py              # Local cores plugin
│                                 #   init_cuerun_plugin() — adds -L, -T
└── tests/
    └── backend/
        ├── test_cue.py           # Serialization and launch tests
        └── test_local.py         # Local dispatch tests
```

## Execution Modes

PyCuerun operates in three distinct modes, selected by CLI flags.

### 1. Launch Mode (default)

Loads an outline script, sets up the session, serializes to XML, and submits to Cuebot.

```text
pycuerun script.outline
```

Flow:

```
load_outline(args[0])
    → (optional) add QC layer if --qc
    → launch_outline(outline, user=options.user)
        → cuerun.launch(outline, **args)
            → OutlineLauncher(outline, **args)
            → launcher.launch(use_pycuerun=True)
                → launcher.setup()
                    → Set frame range, shot, env, name
                    → outline.setup()  (INIT → SETUP → READY)
                → backend.launch(launcher)
                    → serialize(launcher) → XML job spec
                    → opencue.api.launchSpecAndWait(spec)
```

### 2. Execute Mode (`-e`)

Executes a single frame on a render host. Cuebot invokes pycuerun in this mode.

```
pycuerun -e 5-render script.outline
```

Flow:

```
options.execute = "5-render"
    → frame, layer = "5-render".split("-", 1)
    → cuerun.execute_frame(args[0], layer="render", frame="5")
        → ol = load_outline(script)
        → ol.get_layer("render").execute(5)
            → layer._before_execute()
            → layer._execute([5])
            → layer._after_execute()
```

### 3. Inspect Mode (`-i`)

Dumps the outline structure without submitting.

```
pycuerun -i script.outline
```

Flow:

```
options.inspect = "script.outline"
    → ol = load_outline(options.inspect)
    → inspect_script(ol)
        → Print outline full name
        → For each layer:
            → Print layer name
            → Print all layer arguments
```

## CLI Option System

### Option Groups

PyCuerun organizes CLI options into groups via `CuerunOptionParser`:

| Group | Source | Options |
|-------|--------|---------|
| Standard | `CuerunOptionParser.__setup_standard_options` | `-b`, `-s`, `-F`, `-V`, `-D` |
| Development | `CuerunOptionParser.__setup_standard_options` | `-v`, `-r`, `--dev`, `--dev-user`, `--env` |
| Job | `CuerunOptionParser.__setup_standard_options` | `-p`, `-w`, `-t`, `-f`, `--shot`, `--no-mail`, `--max-retries`, `-o`, `--base-name`, `--autoeat` |
| Frame Execution | `PyCuerun.add_my_options` | `-e`, `-i`, `-u`, `-j`, `-m`, `--qc` |
| Plugins | `CuerunOptionParser.add_plugin_option` | Dynamically added (e.g., `-L`, `-T` from local plugin) |

### Two-Phase Argument Handling

Arguments are processed in two phases because some must be resolved before the versioned PyOutline code is imported:

**Phase 1** — `handle_core_arguments()` in `cuerunbase.py`:
Manually scans `sys.argv` for `-V`, `-D`, `-v`, `-r` to set up logging and the PyOutline version/repository before any outline imports.

**Phase 2** — `CuerunOptionParser.parse_args()`:
Full OptionParser processing of all arguments after the versioned code is available.

### Legacy Argument Translation

The `convert_sys_args_from_olrun()` function translates legacy olrun flags before parsing:

```python
translation_dict = {
    '-retry': '-m',    # max retries
    '-jobid': '-j'     # job basename
}
```

### Options-to-Args Conversion

`CuerunOptionParser.options_to_args()` converts the parsed `OptionParser` namespace into a dictionary that `OutlineLauncher` consumes:

```python
{
    "backend", "basename", "server", "pause", "priority",
    "wait", "test", "range", "range_default", "shot",
    "dev", "devuser", "facility", "nomail", "maxretries",
    "os", "env", "autoeat"
}
```

### Frame Range Resolution

`setup_frame_range()` resolves the frame range with fallback:

1. Explicit `-f` / `--range` value
2. Positional argument after the script path
3. `$FR` environment variable (marked as `range_default=True`)
4. `None` (layers use their own ranges)

When `range_default=True`, the range only applies to layers that don't already define their own range.

## Job Serialization Pipeline

When launching to the OpenCue backend, pycuerun serializes the outline into XML.

### XML Job Spec Structure

```xml
<?xml version="1.0"?>
<spec>
  <facility>local</facility>
  <show>testing</show>
  <shot>test</shot>
  <user>artist</user>
  <email>artist@domain</email>
  <uid>1000</uid>

  <job name="my-job">
    <paused>False</paused>
    <maxretries>2</maxretries>
    <autoeat>False</autoeat>
    <os>Linux</os>
    <env>
      <key name="GLOBAL_VAR">value</key>
    </env>

    <layers>
      <layer name="render" type="Render">
        <cmd>wrapper pycuerun -e #IFRAME#-render script.outline ...</cmd>
        <range>1-100</range>
        <chunk>1</chunk>
        <cores>1.0</cores>
        <memory>4194304</memory>
        <services><service>default</service></services>
        <env>
          <key name="LAYER_VAR">value</key>
        </env>
      </layer>
    </layers>
  </job>

  <depends>
    <depend type="FRAME_BY_FRAME" anyframe="False">
      <depjob>my-job</depjob>
      <deplayer>composite</deplayer>
      <onjob>my-job</onjob>
      <onlayer>render</onlayer>
    </depend>
  </depends>
</spec>
```

### Command Wrapping

The `build_command()` function in `backend/cue.py` constructs the per-layer command:

```text
[strace ...] <wrapper> <user_dir> <pycuerun> <script> -e #IFRAME#-<layer> --version <ver> --repos <repos> --debug [--dev] [--dev-user <user>]
```

Where:
- `<wrapper>` is `opencue_wrap_frame` (sets up show/shot environment) or `opencue_wrap_frame_no_ss` (no setshot)
- `#IFRAME#` is replaced by Cuebot with the actual frame number at dispatch time

### Spec Version Gating

The serializer gates features based on `spec_version` from the config:

| Feature | Minimum Version |
|---------|-----------------|
| `timeout`, `timeout_llu` | 1.10 |
| `priority` | 1.11 |
| `gpus`, `gpu_memory` | 1.12 |
| `maxcores`, `maxgpus` | 1.13 |
| `outputs` | 1.15 |

## QC Integration

The `--qc` flag adds a Quality Control layer via `bin/util_qc_job_layer.py`.

### How It Works

1. PyCuerun adds a `Shell` layer named `wait_on_artist_to_qc` that depends on all other layers
2. When the QC layer executes, `util_qc_job_layer.py`:
   - Pauses the entire job
   - Adds a comment instructing the artist to eat the QC frame to release the job
   - Retries the QC frame (keeps it alive for the artist)
3. The artist reviews outputs, then eats the QC frame in CueGUI to allow the job to finish

### Implementation

```python
# In PyCuerun.handle_my_options():
if options.qc:
    outline.add_layer(
        Shell("wait_on_artist_to_qc",
              command=qc_path,
              range="1", setshot=False, threads=0.1, memory=1,
              require=['%s:all' % layer for layer in outline.get_layers()])
    )
```

## Extending PyCuerun

### Creating a Custom Cuerun Tool

Subclass `AbstractCuerun` to create specialized launchers:

```python
from cuerunbase import AbstractCuerun
from optparse import OptionGroup

class MyCuerun(AbstractCuerun):

    usage = "usage: %prog [options] outline_script"
    descr = "Custom cuerun tool for my studio."

    def add_my_options(self):
        parser = self.get_parser()
        group = OptionGroup(parser, "My Custom Options")
        parser.add_option_group(group)
        group.add_option("--scene", action="store", dest="scene",
                         help="Path to the scene file.")

    def handle_my_options(self, parser, options, args):
        from outline import load_outline
        outline = load_outline(args[0])

        if options.scene:
            outline.set_arg("scene_file", options.scene)

        jobs = self.launch_outline(outline)
        for job in jobs:
            print(f"Submitted: {job.data.name}")

if __name__ == '__main__':
    MyCuerun().go()
```

### Adding Plugin CLI Options

Plugins can register options via `init_cuerun_plugin`:

```python
def init_cuerun_plugin(cuerun):
    parser = cuerun.get_parser()
    parser.add_plugin_option(
        "--my-option",
        action="store",
        dest="my_option",
        help="My custom plugin option."
    )
```

Plugin options appear in the "Plugins" option group.

### Adding Launch Events

Listen for launch lifecycle events:

```python
from outline import event

def init_cuerun_plugin(cuerun):
    cuerun.add_event_listener(
        event.BEFORE_LAUNCH,
        on_before_launch
    )

def on_before_launch(evt):
    outline = evt.outline
    # Modify outline before submission
    outline.set_env("SUBMITTED_BY", "my_plugin")
```

## Testing

### Running Tests

```bash
cd pyoutline

# All tests
python -m pytest tests/ -v

# Backend-specific tests (most relevant to pycuerun)
python -m pytest tests/backend/test_cue.py -v
python -m pytest tests/backend/test_local.py -v

# With coverage
python -m pytest tests/ --cov=outline --cov-report=html
```

### Testing Serialization

Verify the XML output without submitting to Cuebot:

```python
import outline
from outline.cuerun import OutlineLauncher

ol = outline.Outline("test-job", show="testing", shot="test")
ol.add_layer(outline.modules.shell.Shell(
    "render", command=["echo", "#IFRAME#"], range="1-10"
))

launcher = OutlineLauncher(ol, pause=True)
launcher.setup()
xml_spec = launcher.serialize(use_pycuerun=False)
print(xml_spec)
```

### Mocking Cuebot

Use `unittest.mock` to test launch without a running Cuebot:

```python
import unittest
from unittest import mock
import outline
from outline.modules.shell import Shell

class PycuerunLaunchTest(unittest.TestCase):

    @mock.patch("opencue.api.launchSpecAndWait")
    def test_launch_submits_spec(self, mock_launch):
        mock_launch.return_value = [mock.MagicMock()]

        ol = outline.Outline("test", show="testing", shot="test")
        ol.add_layer(Shell("layer1", command=["echo", "hi"], range="1-5"))

        jobs = outline.cuerun.launch(ol, use_pycuerun=False)

        mock_launch.assert_called_once()
        spec_xml = mock_launch.call_args[0][0]
        self.assertIn("<layer", spec_xml)
        self.assertIn('name="layer1"', spec_xml)

    @mock.patch("opencue.api.launchSpecAndWait")
    def test_pause_flag(self, mock_launch):
        mock_launch.return_value = [mock.MagicMock()]

        ol = outline.Outline("test", show="testing", shot="test")
        ol.add_layer(Shell("layer1", command=["echo", "hi"], range="1-5"))

        outline.cuerun.launch(ol, use_pycuerun=False, pause=True)

        spec_xml = mock_launch.call_args[0][0]
        self.assertIn("<paused>True</paused>", spec_xml)
```

### Testing Frame Execution

```python
class FrameExecutionTest(unittest.TestCase):

    def test_execute_frame(self):
        """Test that execute_frame loads and runs the correct layer/frame."""
        with mock.patch("outline.loader.load_outline") as mock_load:
            mock_layer = mock.MagicMock()
            mock_ol = mock.MagicMock()
            mock_ol.get_layer.return_value = mock_layer
            mock_load.return_value = mock_ol

            from outline.cuerun import execute_frame
            execute_frame("/path/to/script.outline", "render", "5")

            mock_ol.get_layer.assert_called_with("render")
            mock_layer.execute.assert_called_with(5)
```

## Troubleshooting

### Common Issues

**"You must provide an outline script to execute"**
No script path was given. Ensure the script path is the first positional argument after all flags.

**`ShellCommandFailureException` during `-e` execution**
The frame's command failed. Check the command output in stderr. The exit status is propagated to pycuerun's exit code.

**"No jobs were submitted, check the outline file"**
The outline has no layers, or all layer frame ranges are outside the job's frame range. Use `-i` to inspect the outline structure.

**Frame range not applied**
When `$FR` is set and all layers define their own ranges, the `$FR` range is treated as a default and does not override per-layer ranges. Use explicit `-f` to force a range override.

**Legacy olrun arguments not recognized**
Only `-retry` (→ `-m`) and `-jobid` (→ `-j`) are auto-translated. Other olrun flags must be manually converted.

### Debug Techniques

1. **Inspect the outline**: `pycuerun -i script.outline`
2. **Debug logging**: `pycuerun -D script.outline` — logs option values, backend selection, and XML spec
3. **Local execution**: `pycuerun --backend local script.outline` — run locally without Cuebot
4. **Single frame**: `pycuerun -D -e 1-layer_name script.outline` — execute one frame with debug output
5. **Check generated XML**: Use `OutlineLauncher.serialize()` programmatically to inspect the spec
