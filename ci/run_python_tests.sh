#!/bin/bash

set -e

pip install --user -r requirements.txt -r requirements_gui.txt

# Protos need to have their Python code generated in order for tests to pass.
python -m grpc_tools.protoc -I=proto/ --python_out=pycue/opencue/compiled_proto --grpc_python_out=pycue/opencue/compiled_proto proto/*.proto
python -m grpc_tools.protoc -I=proto/ --python_out=rqd/rqd/compiled_proto --grpc_python_out=rqd/rqd/compiled_proto proto/*.proto

# Fix imports to work in both Python 2 and 3. See
# <https://github.com/protocolbuffers/protobuf/issues/1491> for more info.
sed -i 's/^\(import.*_pb2\)/from . \1/' pycue/opencue/compiled_proto/*.py rqd/rqd/compiled_proto/*.py

python pycue/setup.py test
PYTHONPATH=pycue python pyoutline/setup.py test
PYTHONPATH=pycue python cueadmin/setup.py test
PYTHONPATH=pycue xvfb-run -d python cuegui/setup.py test
PYTHONPATH=pycue:pyoutline python cuesubmit/setup.py test
python rqd/setup.py test
