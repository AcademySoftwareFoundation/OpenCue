#!/bin/bash

# Script for running OpenCue unit tests with PySide2.
#
# This script is written to be run within the OpenCue GitHub Actions environment.
# See `.github/workflows/testing-pipeline.yml`.

set -ex

args=("$@")
python_version=$(python -V 2>&1)
echo "Will run tests using ${python_version}"

pip uninstall --yes opencue_proto opencue_pycue opencue_pyoutline opencue_cueadmin opencue_cueman opencue_cuesubmit opencue_rqd

if [[ -v OPENCUE_PROTO_PACKAGE_PATH ]]
then
  echo "Installing pre-built opencue_proto package"
  pip install ${OPENCUE_PROTO_PACKAGE_PATH}
else
  pip install ./proto
fi

for package in pycue pyoutline cueadmin cueman cuesubmit rqd
do
  PACKAGE_PATH="OPENCUE_${package^^}_PACKAGE_PATH"
  if [[ -v "${PACKAGE_PATH}" ]]
  then
    pip install "${!PACKAGE_PATH}[test]"
  else
    pip install "./${package}[test]"
  fi
  python -m pytest ${package}
done

# Xvfb no longer supports Python 2.
if [[ "$python_version" =~ "Python 3" && ${args[0]} != "--no-gui" ]]; then
  ci/run_gui_test.sh
fi
