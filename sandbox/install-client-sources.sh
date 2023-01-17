#!/bin/bash

set -e

pip install -r requirements.txt
#-r requirements_gui.txt

# Compile the proto used to communicate with the Cuebot server.
cd proto
python -m grpc_tools.protoc -I=. \
  --python_out=../pycue/opencue/compiled_proto \
  --grpc_python_out=../pycue/opencue/compiled_proto ./*.proto
cd ..
2to3 -wn -f import pycue/opencue/compiled_proto/*_pb2*.py

# Install all client packages.
pip install pycue/ pyoutline/ cueadmin/
#cuesubmit/ cuegui/
