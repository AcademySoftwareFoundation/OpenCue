#!/bin/bash

set -ex

if [[ -v VIRTUAL_ENV ]]
then
  PIP_OPT=""
else
  PIP_OPT="--user"
fi

python_version=$(python -V)
echo "Will run Python lint using ${python_version}"

python -m pip install pylint==2.15.10 ${PIP_OPT}
python -m pylint --version

pip uninstall --yes opencue_proto opencue_pycue opencue_pyoutline opencue_cueadmin opencue_cueman opencue_cuesubmit opencue_rqd
if [[ -v OPENCUE_PROTO_PACKAGE_PATH ]]
then
  echo "Installing pre-built cuebot package"
  pip install ${OPENCUE_PROTO_PACKAGE_PATH} ${PIP_OPT}
else
  pip install ./proto ${PIP_OPT}
fi

echo "Running lint for pycue/..."
pip install ./pycue[test] ${PIP_OPT}
cd pycue
python -m pylint --rcfile=../ci/pylintrc_main FileSequence
python -m pylint --rcfile=../ci/pylintrc_main opencue
python -m pylint --rcfile=../ci/pylintrc_test tests
cd ..

echo "Running lint for pyoutline/..."
pip install ./pyoutline[test] ${PIP_OPT}
cd pyoutline
python -m pylint --rcfile=../ci/pylintrc_main outline
python -m pylint --rcfile=../ci/pylintrc_test tests
cd ..

echo "Running lint for cueadmin/..."
pip install ./cueadmin[test] ${PIP_OPT}
cd cueadmin
python -m pylint --rcfile=../ci/pylintrc_main cueadmin
python -m pylint --rcfile=../ci/pylintrc_test tests
cd ..

echo "Running lint for cueman/..."
pip install ./cueman[test] ${PIP_OPT}
cd cueman
python -m pylint --rcfile=../ci/pylintrc_main cueman
python -m pylint --rcfile=../ci/pylintrc_test tests
cd ..

echo "Running lint for cuegui/..."
pip install ./cuegui[test] ${PIP_OPT}
cd cuegui
python -m pylint --rcfile=../ci/pylintrc_main cuegui --ignore=cuegui/images,cuegui/images/crystal --disable=no-member
python -m pylint --rcfile=../ci/pylintrc_test tests --disable=no-member
cd ..

echo "Running lint for cuesubmit/..."
pip install ./cuesubmit[test] ${PIP_OPT}
cd cuesubmit
python -m pylint --rcfile=../ci/pylintrc_main cuesubmit --disable=no-member
python -m pylint --rcfile=../ci/pylintrc_test tests --disable=no-member
cd ..

echo "Running lint for rqd/..."
pip install ./rqd[test] ${PIP_OPT}
cd rqd
python -m pylint --rcfile=../ci/pylintrc_main rqd
python -m pylint --rcfile=../ci/pylintrc_test tests
python -m pylint --rcfile=../ci/pylintrc_test pytests
cd ..
