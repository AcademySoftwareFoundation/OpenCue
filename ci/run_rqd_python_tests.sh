#!/bin/bash

# Script for running OpenCue RQD unit tests with vanilla python
#
# This script is written to be run within the OpenCue GitHub Actions environment.
# See `.github/workflows/testing-pipeline.yml`.

set -e

args=("$@")
python_version=$(python -V 2>&1)
echo "Will run tests using ${python_version}"

pip install --user -r requirements/rqd.txt -r requirements/tests.txt

# Protos need to have their Python code generated in order for tests to pass.
python -m grpc_tools.protoc -I=proto/ --python_out=pycue/opencue/compiled_proto --grpc_python_out=pycue/opencue/compiled_proto proto/*.proto
python -m grpc_tools.protoc -I=proto/ --python_out=rqd/rqd/compiled_proto --grpc_python_out=rqd/rqd/compiled_proto proto/*.proto

# Fix imports to work in both Python 2 and 3. See
# <https://github.com/protocolbuffers/protobuf/issues/1491> for more info.
python ci/fix_compiled_proto.py pycue/opencue/compiled_proto
python ci/fix_compiled_proto.py rqd/rqd/compiled_proto

python -m unittest discover -s pycue/tests -t pycue -p "*.py"
python -m unittest discover -s rqd/tests -t rqd -p "*.py"

