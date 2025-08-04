---
title: "Installing CueAdmin"
nav_order: 8
parent: Getting Started
layout: default
linkTitle: "Installing CueAdmin"
date: 2019-02-22
description: >
  Install the CueAdmin command-line client
---

# Installing CueAdmin

### Install the CueAdmin command-line client

---

CueAdmin is the OpenCue command-line client.

You run this client to administer an OpenCue deployment. It's written in Python
and provides a thin layer over the OpenCue Python API.

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

    > **Note**
> {: .callout .callout-info}Use of a virtual environment isn't
    strictly necessary but is recommended to avoid conflicts with other locally
    installed Pythoy libraries. If you already created a virtual environment
    in which to install PyCue, skip this step and use PyCue's environment for
    the following steps.>

    ```shell
    virtualenv venv
    ```

1.  Evaluate the commands in the `activate` file in your current shell:

    TIP: To review the contents of the `activate` file, run `cat activate`.

    ```shell
    source venv/bin/activate
    ```

### Option 1: Installing a published release

Visit the
[OpenCue releases page](https://github.com/AcademySoftwareFoundation/OpenCue/releases) and
download the cueadmin tarball from the latest release's Assets.

```shell
export CUEADMIN_TAR="<path to cueadmin tar.gz>"
export CUEADMIN_DIR=$(basename "$CUEADMIN_TAR" .tar.gz)
tar xvzf "$CUEADMIN_TAR"
cd "$CUEADMIN_DIR"
pip install -r requirements.txt
python setup.py install
cd ..
```

This installs a `cueadmin` executable in your `PATH`. 

To run `cueadmin`:

```shell
cueadmin -server localhost -ls
```

The above example command lists all shows from a Cuebot instance running on
`localhost`. To display a full list of the functionality CueAdmin provides, run
`cueadmin --help` .

### Option 2: Installing from source

Make sure you've
[checked out the source code](/docs/getting-started/checking-out-the-source-code)
and your current directory is the root of the checked out source.

```shell
pip install -r requirements.txt
cd cueadmin
```

You can either install CueAdmin from here and run the `cueadmin` executable that
gets created:

```shell
python setup.py install
cd ..
cueadmin -server localhost -ls
```

OR you can run the software directly, without installing:

```shell
python ./cueadmin -server localhost -ls
```

The above example command lists all shows from a Cuebot instance running on
`localhost`. To display a full list of the functionality CueAdmin provides, run
`cueadmin --help`.
