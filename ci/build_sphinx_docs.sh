#!/bin/bash

set -e

# Sphinx has some additional requirements
pip install --user -r requirements.txt -r docs/requirements.txt

# Must generate Python code from Protos in order for Sphinx to build the docs.
python -m grpc_tools.protoc -I=proto/ --python_out=pycue/opencue/compiled_proto --grpc_python_out=pycue/opencue/compiled_proto proto/*.proto

# Fix imports to work in both Python 2 and 3. See
# <https://github.com/protocolbuffers/protobuf/issues/1491> for more info.
sed -i 's/^\(import.*_pb2\)/from . \1/' pycue/opencue/compiled_proto/*.py

# Build the docs and treat warnings as errors
~/.local/bin/sphinx-build -W -b html -d docs/_build/doctrees docs docs/_build/html
