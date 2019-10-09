#!/bin/bash

set -e

pip install -r requirements.txt

# Compile the proto used to communicate with the Cuebot server
cd proto
python -m grpc_tools.protoc -I=. \
  --python_out=../pycue/opencue/compiled_proto \
  --grpc_python_out=../pycue/opencue/compiled_proto ./*.proto
cd ..

# Install the OpenCue client packages
# You also need to set the OL_CONFIG environment variable
# to pyoutline/etc/outline.cfg to run Cuesubmit
pip install pycue/ pyoutline/ cuesubmit/ cuegui/ cueadmin/
