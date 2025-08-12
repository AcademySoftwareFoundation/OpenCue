---
title: "Installing CueGUI"
nav_order: 19
parent: Getting Started
layout: default
linkTitle: "Installing CueGUI"
date: 2019-02-22
description: >
  Install CueGUI to monitor, manage, and troubleshoot jobs
---

# Installing CueGUI

### Install CueGUI to monitor, manage, and troubleshoot jobs

---

This guide shows you how to install CueGUI.

Users use CueGUI to monitor and manage OpenCue jobs.

Admins use CueGUI to:

*   Troubleshoot jobs.
*   Assign render processors to jobs.
*   Manage cue priorities.

CueGUI is a standalone PySide application. It runs locally on the user's workstation; all users
within your OpenCue deployment who want to use it will need it available on their workstations. 

## Before you begin

1.  Before you start to work through this guide, complete the steps in
    [Installing PyCue and PyOutline](/docs/getting-started/installing-pycue-and-pyoutline).

1.  You need the same Cuebot hostname that you used to configure PyCue in this
    guide as well. If you don't know the Cuebot hostname, check with your
    OpenCue admin. After you know this, set the `CUEBOT_HOSTNAME_OR_IP`
    environment variable:

    ```shell
    export CUEBOT_HOSTNAME_OR_IP=localhost
    ```

1.  To follow the instructions in this guide, you'll need the following
    software:

    *   [Python](https://www.python.org/)
    *   [pip](https://pypi.org/project/pip/) Python package manager
    *   [virtualenv](https://pypi.org/project/virtualenv/) tool

## Installing CueGUI

CueGUI is written in Python. To run CueGUI, you install a series of dependencies
and configure a virtual environment for the Python code to run inside.

To install CueGUI:

1.  To install the required Python packages, create an isolated Python
    environment:

    > **Note :** Use of a virtual environment isn't
    strictly necessary but is recommended to avoid conflicts with other locally
    installed Python libraries. If you already created a virtual environment in
    which to install PyCue, skip this step and use PyCue's environment for the
    following steps.>

    ```shell
    virtualenv venv
    ```

1.  Evaluate the commands in the `activate` file in your current shell:

    TIP: To review the contents of the `activate` file, run `cat activate`.

    ```shell
    source venv/bin/activate
    ```

### Option 1: Installing from pypi

To install a published release:

To install from the published pypi release:

You need the `pip` and `virtualenv` tools. Use of a virtual environment is not
strictly necessary but is recommended to avoid conflicts with other installed
Python libraries.

```shell
pip install opencue-cuegui
```

Run CueGUI:

```shell
CUEBOT_HOSTS=$CUEBOT_HOSTNAME_OR_IP cuegui
```

### Option 2: Install from source

Make sure you've
[checked out the source code](/docs/getting-started/checking-out-the-source-code)
and your current directory is the root of the checked out source.

```shell
pip install cuegui/
```

You run the `cuegui` executable that gets created:

```shell
CUEBOT_HOSTS=$CUEBOT_HOSTNAME_OR_IP cuegui
```

The CueGUI executable launches and the Cuetopia window appears:

![CueGUI Cuetopia window](/assets/images/cuetopia_default_verify.png)

## What's next?

*   [Installing CueSubmit](/docs/getting-started/installing-cuesubmit)
