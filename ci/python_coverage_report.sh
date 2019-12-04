#!/bin/bash

set -e

pip install --user -r requirements.txt -r requirements_gui.txt

# Protos need to have their Python code generated in order for tests to pass.
python -m grpc_tools.protoc -I=proto/ --python_out=pycue/opencue/compiled_proto --grpc_python_out=pycue/opencue/compiled_proto proto/*.proto
python -m grpc_tools.protoc -I=proto/ --python_out=rqd/rqd/compiled_proto --grpc_python_out=rqd/rqd/compiled_proto proto/*.proto

# Run coverage for each component individually, but append it all into the same report.
coverage run --source=pycue/opencue/,pycue/FileSequence/ --omit=pycue/opencue/compiled_proto/* pycue/setup.py test
PYTHONPATH=pycue coverage run -a --source=pyoutline/outline/ pyoutline/setup.py test
PYTHONPATH=pycue coverage run -a --source=cueadmin/cueadmin/ cueadmin/setup.py test
PYTHONPATH=pycue xvfb-run -d coverage run -a --source=cuegui/cuegui/ cuegui/setup.py test
PYTHONPATH=pycue:pyoutline coverage run -a --source=cuesubmit/cuesubmit/ cuesubmit/setup.py test
coverage run -a --source=rqd/rqd/ --omit=rqd/rqd/compiled_proto/* rqd/setup.py test

# SonarCloud needs the report in XML.
coverage xml
