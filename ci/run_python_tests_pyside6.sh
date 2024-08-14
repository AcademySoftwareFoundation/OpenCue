#!/bin/bash

# Script for running OpenCue unit tests with PySide6.
#
# This script is written to be run within the OpenCue GitHub Actions environment.
# See `.github/workflows/testing-pipeline.yml`.

set -e

python_version=$(python -V 2>&1)
echo "Will run tests using ${python_version}"

# NOTE: To run this in an almalinux environment, install these packages:
# yum -y install \
#   dbus-libs \
#   fontconfig \
#   gcc \
#   libxkbcommon-x11 \
#   mesa-libEGL-devel \
#   python-devel \
#   which \
#   xcb-util-keysyms \
#   xcb-util-image \
#   xcb-util-renderutil \
#   xcb-util-wm \
#   Xvfb

# Install Python requirements.
python3 -m pip install --user -r requirements.txt -r requirements_gui.txt
# Replace PySide2 with PySide6.
python3 -m pip uninstall -y PySide2
python3 -m pip install --user PySide6==6.3.2

# Protos need to have their Python code generated in order for tests to pass.
python -m grpc_tools.protoc -I=proto/ --python_out=pycue/opencue/compiled_proto --grpc_python_out=pycue/opencue/compiled_proto proto/*.proto

# Fix compiled proto code for Python 3.
2to3 -wn -f import pycue/opencue/compiled_proto/*_pb2*.py

python pycue/setup.py test
PYTHONPATH=pycue python pyoutline/setup.py test
PYTHONPATH=pycue python cueadmin/setup.py test
PYTHONPATH=pycue:pyoutline python cuesubmit/setup.py test
python rqd/setup.py test

ci/run_gui_test.sh
