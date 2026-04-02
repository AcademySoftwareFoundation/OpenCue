---
title: "Getting Started with PyOutline and PyCuerun"
nav_order: 32
parent: Getting Started
layout: default
date: 2026-03-13
description: >
  Set up PyOutline and pycuerun for building and submitting OpenCue render jobs
---

# Getting Started with PyOutline and PyCuerun

Set up your environment to build and submit render jobs using PyOutline and pycuerun.

> **Note:** PyOutline is the Python library for building job definitions. PyCuerun is the command-line tool that launches PyOutline scripts to the render farm. Installing PyOutline also installs pycuerun. See [Getting Started with PyCuerun](/docs/getting-started/getting-started-pycuerun/) for CLI-focused setup.

## Before you begin

You need:

- Python 3.7 or later
- A running Cuebot instance (see [Deploying Cuebot](/docs/getting-started/deploying-cuebot/))
- PyCue installed (see [Installing PyCue and PyOutline](/docs/getting-started/installing-pycue-and-pyoutline/))

## Step 1: Install PyOutline

### From PyPI

```bash
pip install opencue-pycue opencue-pyoutline
```

### From source

```bash
cd OpenCue
pip install pycue/
pip install pyoutline/
```

## Step 2: Configure the environment

Set the Cuebot server address:

```bash
export CUEBOT_HOSTS="your-cuebot-hostname"
```

Optionally set show and shot defaults:

```bash
export SHOW="myshow"
export SHOT="myshot"
```

## Step 3: Verify the installation

```bash
python -c "import outline; print('PyOutline installed successfully')"
```

Verify pycuerun is available:

```bash
pycuerun --help
```

## Step 4: Configure PyOutline (optional)

PyOutline reads configuration from the following locations in priority order:

1. Path specified by the `OUTLINE_CONFIG_FILE` environment variable
2. Path specified by the `OL_CONFIG` environment variable (deprecated)
3. `~/.config/opencue/outline.cfg` (user profile)
4. Built-in defaults

Create a custom configuration file if needed:

```ini
[outline]
backend = cue
facility = local
maxretries = 2

[plugin:local]
module = outline.plugins.local
enable = 1
```

## Step 5: Submit your first job

Create `first_job.py`:

```python
import outline
import outline.modules.shell

ol = outline.Outline("first-job", show="testing", shot="test")

layer = outline.modules.shell.Shell(
    "hello",
    command=["echo", "Hello from frame #IFRAME#"],
    range="1-5"
)
ol.add_layer(layer)

outline.cuerun.launch(ol, use_pycuerun=False)
```

Run it:

```bash
python first_job.py
```

Or use pycuerun with an outline script:

```bash
# Create first_job.outline
cat > first_job.outline << 'EOF'
import outline.modules.shell
outline.modules.shell.Shell("hello", command=["echo", "Frame #IFRAME#"], range="1-5")
EOF

pycuerun first_job.outline
```

## Step 6: Monitor your job

Use CueGUI or PyCue to monitor the submitted job:

```python
import opencue
for job in opencue.api.getJobs(show=["testing"]):
    print(f"{job.name()} - {job.state()}")
```
