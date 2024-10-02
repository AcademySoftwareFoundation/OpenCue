#!/bin/bash

set -e

python -m pip install --user -r requirements.txt -r requirements_gui.txt
# Requirements for running the tests on the vfx-platform images
python -m pip install coverage pytest-xvfb

# Protos need to have their Python code generated in order for tests to pass.
python -m grpc_tools.protoc -I=proto/ --python_out=pycue/opencue/compiled_proto --grpc_python_out=pycue/opencue/compiled_proto proto/*.proto
python -m grpc_tools.protoc -I=proto/ --python_out=rqd/rqd/compiled_proto --grpc_python_out=rqd/rqd/compiled_proto proto/*.proto
2to3 -wn -f import pycue/opencue/compiled_proto/*_pb2*.py
2to3 -wn -f import rqd/rqd/compiled_proto/*_pb2*.py

# Run coverage for each component individually, but append it all into the same report.
python -m coverage run --source=pycue/opencue/,pycue/FileSequence/ --omit=pycue/opencue/compiled_proto/* pycue/tests/test_suite.py
PYTHONPATH=pycue python -m coverage run -a --source=pyoutline/outline/ pyoutline/setup.py test
PYTHONPATH=pycue python -m coverage run -a --source=cueadmin/cueadmin/ cueadmin/setup.py test
# TODO: re-enable cuegui tests when xvfb-run gets configured to execute on the new vfx-platform
# PYTHONPATH=pycue xvfb-run -d python -m coverage run -a --source=cuegui/cuegui/ cuegui/setup.py test
PYTHONPATH=pycue:pyoutline python -m coverage run -a --source=cuesubmit/cuesubmit/ cuesubmit/setup.py test
python -m coverage run -a --source=rqd/rqd/ --omit=rqd/rqd/compiled_proto/* rqd/setup.py test

# SonarCloud needs the report in XML.
python -m coverage xml
