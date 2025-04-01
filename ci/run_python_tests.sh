#!/bin/bash

# Script for running OpenCue unit tests with PySide2.
#
# This script is written to be run within the OpenCue GitHub Actions environment.
# See `.github/workflows/testing-pipeline.yml`.

set -ex

args=("$@")
python_version=$(python -V 2>&1)
echo "Will run tests using ${python_version}"

pip uninstall --yes opencue_cuebot opencue_pycue opencue_pyoutline opencue_cueadmin opencue_cuesubmit opencue_rqd
if "${CUBOT_PACKAGE_PATH}"
then
  echo "Installing pre-built cuebot package"
  pip install "${CUBOT_PACKAGE_PATH}"
else
  pip install ./cuebot
fi

pip install ./pycue[test]
python -m pytest pycue

pip install ./pyoutline[test]
python -m pytest pyoutline

pip install ./cueadmin[test]
python -m pytest cueadmin

pip install ./cuesubmit[test]
python -m pytest cuesubmit

pip install ./rqd[test]
python -m pytest rqd/tests
python -m pytest rqd/pytests

# Xvfb no longer supports Python 2.
if [[ "$python_version" =~ "Python 3" && ${args[0]} != "--no-gui" ]]; then
  ci/run_gui_test.sh
fi
