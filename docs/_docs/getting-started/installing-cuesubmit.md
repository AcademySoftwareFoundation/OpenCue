---
title: "Installing CueSubmit"
nav_order: 20
parent: Getting Started
layout: default
linkTitle: "Installing CueSubmit"
date: 2019-02-22
description: >
  Install CueSubmit to submit render jobs
---

# Installing CueSubmit

### Install CueSubmit to submit render jobs

---

The OpenCue job submission GUI.

This is a [Python-based QT](https://www.qt.io/qt-for-python) app through which
you can submit jobs to an OpenCue deployment. It can run as a standalone
application, or as a plug-in for applications that support
[PySide2](https://pypi.org/project/PySide2/) integration, such as Autodesk's
Maya or Foundry's Nuke.

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

## Installing CueSubmit standalone

CueSubmit is written in Python. To run CueSubmit, you install a series of
dependencies and configure a virtual environment for the Python code to run
inside.

1.  To install the required Python packages, create an isolated Python
    environment:

    > **Note**
> {: .callout .callout-info}Use of a virtual environment isn't
    strictly necessary but is recommended to avoid conflicts with other
    locally installed Python libraries. If you already created a virtual
    environment in which to install PyCue, skip this step and use PyCue's
    environment for the following steps.>

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
pip install opencue-cuesubmit
```

Run CueSubmit:

```shell
CUEBOT_HOSTS=$CUEBOT_HOSTNAME_OR_IP cuesubmit
```

### Option 2: Installing from source

Make sure you've
[checked out the source code](/docs/getting-started/checking-out-the-source-code)
and your current directory is the root of the checked out source.

```shell
pip install cuesubmit/
```

You run the `cuesubmit` executable that gets created:

```shell
CUEBOT_HOSTS=$CUEBOT_HOSTNAME_OR_IP cuesubmit
```

## Installing CueSubmit plug-ins

CueSubmit comes packaged with plug-ins for Maya and Nuke. These plug-ins can
serve as a template if you wish to write new plug-ins on your own.

### Installing the Maya plug-in

To install the Maya plug-in:

1.  Create or locate your `Maya.env` file as described in
    [Setting environment variables using Maya.env](https://knowledge.autodesk.com/support/maya/learn-explore/caas/CloudHelp/cloudhelp/2018/ENU/Maya-EnvVar/files/GUID-8EFB1AC1-ED7D-4099-9EEE-624097872C04-htm.html).

1.  Add one of the following blocks of code, depending on your operating system:

    - For macOS and Linux:
    
      ```shell
      # Point Maya to the CueSubmit install.
      PYTHONPATH=$PYTHONPATH:<cuesubmit install path>/plugins/maya
      XBMLANGPATH=$XBMLANGPATH:<cuesubmit install path>/plugins/maya
      # Help OpenCue find the required library dependencies.
      CUE_PYTHONPATH=<path to virtualenv>/lib/python2.7/site-packages
      # The hostname of your Cuebot instance.
      CUEBOT_HOSTS=localhost
      ```

    - For Windows:

      ```shell
      # Point Maya to the CueSubmit install.
      PYTHONPATH=$PYTHONPATH;<cuesubmit install path>/plugins/maya
      XBMLANGPATH=$XBMLANGPATH;<cuesubmit install path>/plugins/maya
      # Help OpenCue find the required library dependencies.
      CUE_PYTHONPATH=<path to virtualenv>/lib/python2.7/site-packages
      # The hostname of your Cuebot instance.
      CUEBOT_HOSTS=localhost
      ```

1.  Restart Maya.

Maya should now contain a new "OpenCue" shelf with a single "Render on OpenCue"
item.

### Installing the Nuke plug-in

To install the Nuke plug-in:

1.  Create a `menu.py` file or locate your existing one as described in
    [Defining Custom Menus and Toolbars](https://learn.foundry.com/nuke/content/comp_environment/configuring_nuke/custom_menus_toolbars.html).

1.  Add the following content:

    ```python
    import os
    import nuke
    # Path to Python binary used to execute the CueSubmit app. If you set up
    # virtualenv, use this path. If you're using a systemwide Python install,
    # you can probably set this to be just "python".
    os.environ['CUE_PYTHON_BIN'] = '<path to virtualenv>/bin/python'
    # Hostname of your Cuebot instance.
    os.environ['CUEBOT_HOSTS'] = 'localhost'
    nuke.pluginAddPath('<path to cuesubmit install>/plugins/nuke')
    ```

1.  Restart Nuke.

Nuke should now contain a new menu item "Render > Render on OpenCue".

## What's next?

*   [Installing CueAdmin](/docs/getting-started/installing-cueadmin)
*   [CueGUI reference](/docs/reference/cuegui-reference)
