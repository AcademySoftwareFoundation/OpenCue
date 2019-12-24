#!/bin/bash

set -e

# Sphinx has some additional requirements
pip install --user -r requirements.txt -r docs/requirements.txt

# Must generate Python code from Protos in order for Sphinx to build the docs.
python -m grpc_tools.protoc -I=proto/ --python_out=pycue/opencue/compiled_proto --grpc_python_out=pycue/opencue/compiled_proto proto/*.proto

pip show sphinx

# Build the docs and treat warnings as errors
.local/bin/sphinx-build -W -b html -d docs/_build/doctrees docs docs/_build/html
