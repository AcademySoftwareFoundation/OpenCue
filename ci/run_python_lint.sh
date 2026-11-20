#!/bin/bash

# Lints OpenCue's Python packages.
#
# With no arguments, installs pylint and every package, then lints them all. With package
# names (e.g. `ci/run_python_lint.sh cueadmin`), lints only those, which must already be
# installed along with pylint.

set -ex

lint_package() {
  local package="$1"
  echo "Running lint for ${package}/..."
  pushd "${package}"
  case "${package}" in
    pycue)
      python -m pylint --rcfile=../ci/pylintrc_main FileSequence
      python -m pylint --rcfile=../ci/pylintrc_main opencue
      python -m pylint --rcfile=../ci/pylintrc_test tests
      ;;
    pyoutline)
      python -m pylint --rcfile=../ci/pylintrc_main outline
      python -m pylint --rcfile=../ci/pylintrc_test tests
      ;;
    cuegui)
      python -m pylint --rcfile=../ci/pylintrc_main cuegui --ignore=cuegui/images,cuegui/images/crystal --disable=no-member
      python -m pylint --rcfile=../ci/pylintrc_test tests --disable=no-member
      ;;
    cuesubmit)
      python -m pylint --rcfile=../ci/pylintrc_main cuesubmit --disable=no-member
      python -m pylint --rcfile=../ci/pylintrc_test tests --disable=no-member
      ;;
    rqd)
      python -m pylint --rcfile=../ci/pylintrc_main rqd
      python -m pylint --rcfile=../ci/pylintrc_test tests
      python -m pylint --rcfile=../ci/pylintrc_test pytests
      ;;
    cueadmin|cueman|cuecmd|cuenimby)
      python -m pylint --rcfile=../ci/pylintrc_main "${package}"
      python -m pylint --rcfile=../ci/pylintrc_test tests
      ;;
    *)
      echo "Unknown package ${package}"
      exit 1
      ;;
  esac
  popd
}

if [[ $# -gt 0 ]]; then
  for package in "$@"; do
    lint_package "${package}"
  done
  exit 0
fi

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

pip uninstall --yes opencue_proto opencue_pycue opencue_pyoutline opencue_cueadmin opencue_cueman opencue_cuecmd opencue_cuesubmit opencue_rqd
if [[ -v OPENCUE_PROTO_PACKAGE_PATH ]]
then
  echo "Installing pre-built cuebot package"
  pip install ${OPENCUE_PROTO_PACKAGE_PATH} ${PIP_OPT}
else
  pip install ./proto ${PIP_OPT}
fi

for package in pycue pyoutline cueadmin cueman cuecmd cuegui cuesubmit cuenimby rqd; do
  pip install "./${package}[test]" ${PIP_OPT}
  lint_package "${package}"
done
