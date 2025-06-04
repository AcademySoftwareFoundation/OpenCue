---
title: "Installing PyCue and PyOutline"
linkTitle: "Installing PyCue and PyOutline"
weight: 5
date: 2019-02-22
description: >
  Install the OpenCue Python API and related Python library
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

{{% alert title="Note" color="info"%}}If you install PyCue into a virtual environment,
other tools which make use of PyCue must run within the same
environment.{{% /alert %}}

## Installing PyCue and PyOutline

To install PyCue and PyOutline, you can either download a published release or
install the library directly from source.

### Option 1: Installing a published release

To install a published release, visit the
[OpenCue releases page](https://github.com/AcademySoftwareFoundation/OpenCue/releases) and
download the `pycue` and `pyoutline` tarballs from the list of assets for the
latest release.

Install PyCue:

```shell
export PYCUE_TAR="<path to pycue tar.gz>"
export PYCUE_DIR=$(basename "$PYCUE_TAR" .tar.gz)
virtualenv venv # If you previously created a virtualenv, skip this step.
source venv/bin/activate
tar xvzf "$PYCUE_TAR"
cd "$PYCUE_DIR"
pip install -r requirements.txt
python setup.py install
cd ..
rm -rf "$PYCUE_DIR"
```

Then follow the same steps to install PyOutline:

```shell
export PYOUTLINE_TAR="<path to pyoutline tar.gz>"
export PYOUTLINE_DIR=$(basename "$PYOUTLINE_TAR" .tar.gz)
tar xvzf "$PYOUTLINE_TAR"
cd "$PYOUTLINE_DIR"
pip install -r requirements.txt
python setup.py install
cd ..
rm -rf "$PYOUTLINE_DIR"
```

### Option 2: Installing from source

Make sure you've
[checked out the source code](/docs/getting-started/checking-out-the-source-code)
and your current directory is the root of the checked out source.

Install PyCue:

```shell
virtualenv venv  # If you previously created a virtualenv, skip this step.
source venv/bin/activate
pip install -r requirements.txt
cd proto
python -m grpc_tools.protoc -I=. --python_out=../pycue/opencue/compiled_proto --grpc_python_out=../pycue/opencue/compiled_proto ./*.proto
cd ../pycue/opencue/compiled_proto
2to3 -w -n *
cd ../..
python setup.py install
```

Then install PyOutline:

```shell
cd ../pyoutline
python setup.py install
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

{{% alert title="Note" color="info" %}}The exact contents of the list might be different,
depending on the contents of your database.{{% /alert %}}

```
[u'testing']
```

## What's next?

*   [Installing CueGUI](/docs/getting-started/installing-cuegui)
