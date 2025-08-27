---
title: "Installing PyCue and PyOutline"
nav_order: 17
parent: Getting Started
layout: default
linkTitle: "Installing PyCue and PyOutline"
date: 2019-02-22
description: >
  Install the OpenCue Python API and related Python library
---

# Installing PyCue and PyOutline

### Install the OpenCue Python API and related Python library

---

PyCue is the OpenCue Python API. OpenCue client-side Python tools, such as
CueGUI and CueAdmin, all use PyCue for communication with your OpenCue
deployment.

PyOutline is a Python library. It provides a Python interface to the job
specification XML, allowing you to construct complex jobs with Python code
instead of working directly with XML. PyOutline is used by CueSubmit to
construct its job submissions.

Install the PyCue and PyOutline libraries on the systems of all users
that want to use them. Make sure you also install PyCue and PyOutline on all
systems that run tools such as CueGUI and CueSubmit, which depend on the
libraries.

## Before you begin

PyCue requires a Cuebot deployment to communicate with. Ask the admin of your
OpenCue deployment what your Cuebot hostname is. If you're the admin, you can
follow [Deploying Cuebot](/docs/getting-started/deploying-cuebot) to create
your Cuebot instance.

You also need the Python `pip` and `virtualenv` tools. Use of a virtual
environment isn't strictly necessary but is recommended to avoid conflicts with
other installed Python libraries.

> **Note**
> {: .callout .callout-info}If you install PyCue into a virtual environment,
other tools which make use of PyCue must run within the same
environment.>

## Installing PyCue and PyOutline

To install PyCue and PyOutline, you can either download a published release or
install the library directly from source.

### Option 1: Installing from pypi

To install a published release:

To install from the published pypi release:

You need the `pip` and `virtualenv` tools. Use of a virtual environment is not
strictly necessary but is recommended to avoid conflicts with other installed
Python libraries.

```shell
pip install opencue-pycue
```


Then follow the same steps to install PyOutline:

```shell
pip install opencue-pyotline
```

### Option 2: Installing from source

Make sure you've
[checked out the source code](/docs/getting-started/checking-out-the-source-code)
and your current directory is the root of the checked out source.

Install PyCue:

```shell
virtualenv venv  # If you previously created a virtualenv, skip this step.
source venv/bin/activate
pip install pycue/
```

Then install PyOutline:

```shell
pip install pyoutline/
```

## Configuring and verifying the install

If you installed PyCue into a virtual environment, make sure you've activated
that environment.

Run the following commands to set the `CUEBOT_HOSTS` environment variable and
verify the installation:

```shell
CUEBOT_HOSTS="localhost" python
import opencue
import outline
[show.name() for show in opencue.api.getShows()]
```

The expected output of `show.name()` is a list of the shows present in your
OpenCue database:

> **Note**
> {: .callout .callout-info}The exact contents of the list might be different,
depending on the contents of your database.>

```
[u'testing']
```

## What's next?

*   [Installing CueGUI](/docs/getting-started/installing-cuegui)
