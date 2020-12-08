#!/bin/bash

set -e

pip install --user -r requirements.txt -r requirements_gui.txt

# Protos need to have their Python code generated in order for tests to pass.
python -m grpc_tools.protoc -I=proto/ --python_out=pycue/opencue/compiled_proto --grpc_python_out=pycue/opencue/compiled_proto proto/*.proto
python -m grpc_tools.protoc -I=proto/ --python_out=rqd/rqd/compiled_proto --grpc_python_out=rqd/rqd/compiled_proto proto/*.proto

# Fix imports to work in both Python 2 and 3. See
# <https://github.com/protocolbuffers/protobuf/issues/1491> for more info.
2to3 -wn -f import pycue/opencue/compiled_proto/*_pb2*.py
2to3 -wn -f import rqd/rqd/compiled_proto/*_pb2*.py

python pycue/setup.py test
PYTHONPATH=pycue python pyoutline/setup.py test
PYTHONPATH=pycue python cueadmin/setup.py test
PYTHONPATH=pycue xvfb-run -d python cuegui/setup.py test
PYTHONPATH=pycue:pyoutline python cuesubmit/setup.py test
python rqd/setup.py test

# Some environments don't have pylint available, for ones that do they should pass this flag.
if [[ "$1" == "--lint" ]]; then
  cd pyoutline && PYTHONPATH=../pycue python -m pylint --rcfile=../ci/pylintrc_main outline && cd ..
  cd pyoutline && PYTHONPATH=../pycue python -m pylint --rcfile=../ci/pylintrc_test tests && cd ..
fi
