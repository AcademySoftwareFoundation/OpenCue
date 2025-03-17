#!/bin/bash

set -ex

python_version=$(python -V)
echo "Will run Python lint using ${python_version}"

pip install --upgrade pip
pip install pylint==2.15.10 future==1.0.0 grpcio==1.69.0 grpcio-tools==1.69.0 mock==2.0.0 packaging==24.1 psutil==5.9.8 pyfakefs==5.2.3 pynput==1.7.6 PyYAML==5.1 six==1.16.0 pytest==8.3.3 QtPy==2.4.1 PySide6==6.5.3

pip install -e ./cuebot
./ci/build_proto.sh
pip install -e ./cuebot

echo "Running lint for pycue/..."
pip install -e ./pycue
cd pycue
python -m pylint --rcfile=../ci/pylintrc_main FileSequence
python -m pylint --rcfile=../ci/pylintrc_main opencue
python -m pylint --rcfile=../ci/pylintrc_test tests
cd ..

echo "Running lint for pyoutline/..."
pip install ./pyoutline
cd pyoutline
python -m pylint --rcfile=../ci/pylintrc_main outline
python -m pylint --rcfile=../ci/pylintrc_test tests
cd ..

echo "Running lint for cueadmin/..."
pip install ./cueadmin
cd cueadmin
python -m pylint --rcfile=../ci/pylintrc_main cueadmin
python -m pylint --rcfile=../ci/pylintrc_test tests
cd ..

echo "Running lint for cuegui/..."
pip install ./cuegui
cd cuegui
python -m pylint --rcfile=../ci/pylintrc_main cuegui --ignore=cuegui/images,cuegui/images/crystal --disable=no-member
python -m pylint --rcfile=../ci/pylintrc_test tests --disable=no-member
cd ..

echo "Running lint for cuesubmit/..."
pip install ./cuesubmit
cd cuesubmit
python -m pylint --rcfile=../ci/pylintrc_main cuesubmit --disable=no-member
python -m pylint --rcfile=../ci/pylintrc_test tests --disable=no-member
cd ..

echo "Running lint for rqd/..."
pip install ./rqd
cd rqd
python -m pylint --rcfile=../ci/pylintrc_main rqd --ignore=rqd/compiled_proto
python -m pylint --rcfile=../ci/pylintrc_test tests
python -m pylint --rcfile=../ci/pylintrc_test pytests
cd ..
