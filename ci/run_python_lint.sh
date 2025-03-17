#!/bin/bash

set -ex

python_version=$(python -V)
echo "Will run Python lint using ${python_version}"

python -m pip install pylint==2.15.10 --user
python -m pylint --version

pip install ./cuebot --user

echo "Running lint for pycue/..."
pip install ./pycue[test] --user
cd pycue
python -m pylint --rcfile=../ci/pylintrc_main FileSequence
python -m pylint --rcfile=../ci/pylintrc_main opencue
python -m pylint --rcfile=../ci/pylintrc_test tests
cd ..

echo "Running lint for pyoutline/..."
pip install ./pyoutline[test] --user
cd pyoutline
python -m pylint --rcfile=../ci/pylintrc_main outline
python -m pylint --rcfile=../ci/pylintrc_test tests
cd ..

echo "Running lint for cueadmin/..."
pip install ./cueadmin[test] --user
cd cueadmin
python -m pylint --rcfile=../ci/pylintrc_main cueadmin
python -m pylint --rcfile=../ci/pylintrc_test tests
cd ..

echo "Running lint for cuegui/..."
pip install ./cuegui[test] --user
cd cuegui
python -m pylint --rcfile=../ci/pylintrc_main cuegui --ignore=cuegui/images,cuegui/images/crystal --disable=no-member
python -m pylint --rcfile=../ci/pylintrc_test tests --disable=no-member
cd ..

echo "Running lint for cuesubmit/..."
pip install ./cuesubmit[test] --user
cd cuesubmit
python -m pylint --rcfile=../ci/pylintrc_main cuesubmit --disable=no-member
python -m pylint --rcfile=../ci/pylintrc_test tests --disable=no-member
cd ..

echo "Running lint for rqd/..."
pip install ./rqd[test] --user
cd rqd
python -m pylint --rcfile=../ci/pylintrc_main rqd
python -m pylint --rcfile=../ci/pylintrc_test tests
python -m pylint --rcfile=../ci/pylintrc_test pytests
cd ..
