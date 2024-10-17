#!/bin/bash

set -e

python_version=$(python -V)
echo "Will run Python lint using ${python_version}"

pip install --user -r requirements.txt -r requirements_gui.txt

# Protos need to have their Python code generated in order for tests to pass.
python -m grpc_tools.protoc -I=proto/ --python_out=pycue/opencue/compiled_proto --grpc_python_out=pycue/opencue/compiled_proto proto/*.proto
python -m grpc_tools.protoc -I=proto/ --python_out=rqd/rqd/compiled_proto --grpc_python_out=rqd/rqd/compiled_proto proto/*.proto

# Fix imports to work in both Python 2 and 3. See
# <https://github.com/protocolbuffers/protobuf/issues/1491> for more info.
2to3 -wn -f import pycue/opencue/compiled_proto/*_pb2*.py
2to3 -wn -f import rqd/rqd/compiled_proto/*_pb2*.py

echo "Running lint for pycue/..."
cd pycue
python -m pylint --rcfile=../ci/pylintrc_main FileSequence
python -m pylint --rcfile=../ci/pylintrc_main opencue --ignore=opencue/compiled_proto
python -m pylint --rcfile=../ci/pylintrc_test tests
cd ..

echo "Running lint for pyoutline/..."
cd pyoutline
PYTHONPATH=../pycue python -m pylint --rcfile=../ci/pylintrc_main outline
PYTHONPATH=../pycue python -m pylint --rcfile=../ci/pylintrc_test tests
cd ..

echo "Running lint for cueadmin/..."
cd cueadmin
PYTHONPATH=../pycue python -m pylint --rcfile=../ci/pylintrc_main cueadmin
PYTHONPATH=../pycue python -m pylint --rcfile=../ci/pylintrc_test tests
cd ..

echo "Running lint for cuegui/..."
cd cuegui
PYTHONPATH=../pycue python -m pylint --rcfile=../ci/pylintrc_main cuegui --ignore=cuegui/images,cuegui/images/crystal
PYTHONPATH=../pycue python -m pylint --rcfile=../ci/pylintrc_test tests
cd ..

echo "Running lint for cuesubmit/..."
cd cuesubmit
PYTHONPATH=../pycue:../pyoutline python -m pylint --rcfile=../ci/pylintrc_main cuesubmit
PYTHONPATH=../pycue:../pyoutline python -m pylint --rcfile=../ci/pylintrc_test tests
cd ..

echo "Running lint for rqd/..."
cd rqd
PYTHONPATH=../pycue python -m pylint --rcfile=../ci/pylintrc_main rqd --ignore=rqd/compiled_proto
PYTHONPATH=../pycue python -m pylint --rcfile=../ci/pylintrc_test tests
cd ..
