#!/bin/bash

# Script for running OpenCue unit tests with PySide2.
#
# This script is written to be run within the OpenCue GitHub Actions environment.
# See `.github/workflows/testing-pipeline.yml`.

set -e

args=("$@")
python_version=$(python -V 2>&1)
echo "Will run tests using ${python_version}"

pip install --user -r requirements.txt -r requirements_gui.txt

# Protos need to have their Python code generated in order for tests to pass.
python -m grpc_tools.protoc -I=proto/ --python_out=pycue/opencue/compiled_proto --grpc_python_out=pycue/opencue/compiled_proto proto/*.proto
python -m grpc_tools.protoc -I=proto/ --python_out=rqd/rqd/compiled_proto --grpc_python_out=rqd/rqd/compiled_proto proto/*.proto

# Fix imports to work in both Python 2 and 3. See
# <https://github.com/protocolbuffers/protobuf/issues/1491> for more info.
2to3 -wn -f import pycue/opencue/compiled_proto/*_pb2*.py
2to3 -wn -f import rqd/rqd/compiled_proto/*_pb2*.py

python3 -m unittest discover -s pycue/tests -t pycue -p "*.py"
PYTHONPATH=pycue python3 -m unittest discover -s pyoutline/tests -t pyoutline -p "*.py"
PYTHONPATH=pycue python3 -m unittest discover -s cueadmin/tests -t cueadmin -p "*.py"
PYTHONPATH=pycue:pyoutline python3 -m unittest discover -s cuesubmit/tests -t cuesubmit -p "*.py"
python3 -m unittest discover -s rqd/tests -t rqd -p "*.py"


# Xvfb no longer supports Python 2.
if [[ "$python_version" =~ "Python 3" && ${args[0]} != "--no-gui" ]]; then
  ci/run_gui_test.sh
fi
