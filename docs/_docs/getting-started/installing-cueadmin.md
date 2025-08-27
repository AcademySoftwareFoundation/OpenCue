---
title: "Installing CueAdmin"
nav_order: 18
parent: Getting Started
layout: default
linkTitle: "Installing CueAdmin"
date: 2025-08-11
description: >
  Install CueAdmin, the primary command-line administration tool for OpenCue
---

# Installing CueAdmin

### Install CueAdmin, the command-line administration tool for OpenCue

---

CueAdmin is the essential command-line interface for administering OpenCue deployments. It provides control over shows, allocations, hosts, and system resources.

You run CueAdmin to manage your OpenCue infrastructure, configure resources, and monitor system state. It's written in Python and provides an interface to the OpenCue Python API.

## Before you begin

Before you start to work through this guide, complete the steps in
[Installing PyCue and PyOutline](/docs/getting-started/installing-pycue-and-pyoutline).

You need the same Cuebot hostname that you used to configure PyCue in this guide
as well. If you don't know the Cuebot hostname, check with your OpenCue admin.

To follow the instructions in this guide, you'll need the following software:

*   [Python](https://www.python.org/)
*   [pip](https://pypi.org/project/pip/) Python package manager
*   [virtualenv](https://pypi.org/project/virtualenv/) tool

## Installing CueAdmin

CueAdmin is written in Python. To run CueAdmin, you install a series of
dependencies and configure a virtual environment for the Python code to run
inside.

1.  To install the required Python packages, create an isolated Python
    environment:

    > **Note :** Use of a virtual environment isn't
    strictly necessary but is recommended to avoid conflicts with other locally
    installed Pythoy libraries. If you already created a virtual environment
    in which to install PyCue, skip this step and use PyCue's environment for
    the following steps.

    ```shell
    virtualenv venv
    ```

2.  Evaluate the commands in the `activate` file in your current shell:

    TIP: To review the contents of the `activate` file, run `cat activate`.

    ```shell
    source venv/bin/activate
    ```

### Option 1: Installing from pypi

To install from the published pypi release:

You need the `pip` and `virtualenv` tools. Use of a virtual environment is not
strictly necessary but is recommended to avoid conflicts with other installed
Python libraries.

```shell
pip install opencue-cueadmin
```

This installs a `cueadmin` executable in your `PATH`. 

To run `cueadmin`:

```shell
cueadmin -server localhost -ls
```

The above example command lists all shows from a Cuebot instance running on
`localhost`. To display a full list of the functionality CueAdmin provides, run
`cueadmin --help`.

### Option 2: Installing from source

Make sure you've
[checked out the source code](/docs/getting-started/checking-out-the-source-code)
and your current directory is the root of the checked out source.

```shell
pip install cueadmin/
```

To verify installation and see available commands:

```shell
cueadmin --help
```

## Using CueAdmin

### Essential Commands

Once installed, you can start using CueAdmin for system administration:

```bash
# List all shows
cueadmin -ls

# List all allocations
cueadmin -la

# List hosts
cueadmin -lh

# List running jobs
cueadmin -lj
```

### Common Administrative Tasks

Here are some essential tasks you can perform with CueAdmin:

**Managing Shows:**
```bash
# Create a new show
cueadmin -create-show my_show

# Enable/disable a show
cueadmin -enable-show my_show
cueadmin -disable-show my_show
```

**Managing Hosts:**
```bash
# First, list hosts to see what's available
cueadmin -lh

# Lock hosts for maintenance (replace with actual hostname)
cueadmin -host <hostname> -lock

# Move hosts to different allocation (replace with actual hostname and allocation)
cueadmin -host <hostname> -move <allocation_name>
```

**Managing Subscriptions:**
```bash
# First, list existing shows and allocations to see what's available
cueadmin -ls    # List shows
cueadmin -la    # List allocations

# Create subscription (show, allocation, size, burst)
# Replace 'my_show' with your show name and 'local.general' with your allocation
cueadmin -create-sub my_show local.general 100 150
```

### Safety Notes

CueAdmin can perform production-impacting operations. Always:
- Use confirmation prompts (avoid `-force` unless necessary for workarounds)
- Test commands with `-verbose` flag first
- Check the [CueAdmin Reference](/docs/reference/tools/cueadmin/) for detailed documentation

## Next Steps

- Follow the [CueAdmin Tutorial](/docs/tutorials/cueadmin-tutorial/) for hands-on practice
- Review the [CueAdmin Reference](/docs/reference/tools/cueadmin/) for complete command documentation
- Learn about [Cueman](/docs/reference/tools/cueman/) for job management tasks
