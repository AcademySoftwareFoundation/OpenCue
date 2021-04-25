#!/bin/bash

set -e

python_version=$(python3 -V)
echo "Will run tests using ${python_version}"

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
PYTHONPATH=pycue:pyoutline python cuesubmit/setup.py test
python rqd/setup.py test

# Xvfb no longer supports Python 2.
if [[ "$python_version" =~ "Python 3" ]]; then
  PYTHONPATH=pycue xvfb-run -d python cuegui/setup.py test
fi

# Some environments don't have pylint available, for ones that do they should pass this flag.
if [[ "$1" == "--lint" ]]; then
  cd pycue && python -m pylint --rcfile=../ci/pylintrc_main FileSequence && cd ..
  cd pycue && python -m pylint --rcfile=../ci/pylintrc_main opencue --ignore=opencue/compiled_proto && cd ..
  cd pycue && python -m pylint --rcfile=../ci/pylintrc_test tests && cd ..

  cd pyoutline && PYTHONPATH=../pycue python -m pylint --rcfile=../ci/pylintrc_main outline && cd ..
  cd pyoutline && PYTHONPATH=../pycue python -m pylint --rcfile=../ci/pylintrc_test tests && cd ..

  cd cueadmin && PYTHONPATH=../pycue python -m pylint --rcfile=../ci/pylintrc_main cueadmin && cd ..
  cd cueadmin && PYTHONPATH=../pycue python -m pylint --rcfile=../ci/pylintrc_test tests && cd ..

  cd cuegui && PYTHONPATH=../pycue python -m pylint --rcfile=../ci/pylintrc_main cuegui --ignore=cuegui/images,cuegui/images/crystal && cd ..
  cd cuegui && PYTHONPATH=../pycue python -m pylint --rcfile=../ci/pylintrc_test tests && cd ..

  cd cuesubmit && PYTHONPATH=../pycue:../pyoutline python -m pylint --rcfile=../ci/pylintrc_main cuesubmit && cd ..
  cd cuesubmit && PYTHONPATH=../pycue:../pyoutline python -m pylint --rcfile=../ci/pylintrc_test tests && cd ..

  cd rqd && python -m pylint --rcfile=../ci/pylintrc_main rqd --ignore=rqd/compiled_proto && cd ..
  cd rqd && python -m pylint --rcfile=../ci/pylintrc_test tests && cd ..
fi

