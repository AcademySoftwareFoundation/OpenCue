#!/bin/bash

# Script for testing CueGUI with PySide6.
#
# This script is written to be run within an almalinux environment in the OpenCue
# GitHub Actions environment. See .github/workflows/testing-pipeline.yml.

set -e

# Install needed packages.
yum -y install \
  dbus-libs \
  fontconfig \
  gcc \
  libxkbcommon-x11 \
  mesa-libEGL-devel \
  python-devel \
  which \
  xcb-util-keysyms \
  xcb-util-image \
  xcb-util-renderutil \
  xcb-util-wm \
  Xvfb

# Install Python requirements.
python3 -m pip install --user -r requirements.txt -r requirements_gui.txt
# Replace PySide2 with PySide6.
python3 -m pip uninstall -y PySide2
python3 -m pip install --user PySide6==6.3.2

# Fix compiled proto code for Python 3.
python3 -m grpc_tools.protoc -I=proto/ --python_out=pycue/opencue/compiled_proto --grpc_python_out=pycue/opencue/compiled_proto proto/*.proto
python -m grpc_tools.protoc -I=proto/ --python_out=rqd/rqd/compiled_proto --grpc_python_out=rqd/rqd/compiled_proto proto/*.proto
2to3 -wn -f import pycue/opencue/compiled_proto/*_pb2*.py
2to3 -wn -f import rqd/rqd/compiled_proto/*_pb2*.py

# Run tests.
ci/run_gui_test.sh
