#!/bin/bash

# Script for running OpenCue unit tests with PySide2.
#
# This script is written to be run within the OpenCue GitHub Actions environment.
# See `.github/workflows/testing-pipeline.yml`.

set -e

args=("$@")
python_version=$(python -V 2>&1)
echo "Will run tests using ${python_version}"
if [ -z "$VIRTUAL_ENV" ]; then
  pip install -r requirements.txt -r requirements_gui.txt
else
  pip install --user -r requirements.txt -r requirements_gui.txt
fi

# Some rqd unit tests require docker api
pip install docker==7.1.0

# Some rqd unit tests require lokiclient
pip install loki-urllib3-client

pip uninstall --yes opencue_cuebot
pip uninstall --yes opencue_pycue
pip uninstall --yes opencue_pyoutline
pip uninstall --yes opencue_cueadmin
pip uninstall --yes opencue_cuesubmit

./ci/build_proto.sh
pip install -e cuebot

python -m unittest discover -s pycue/tests -t pycue -p "*.py"
pip install -e pycue

python -m unittest discover -s pyoutline/tests -t pyoutline -p "*.py"
pip install -e pyoutline

python -m unittest discover -s cueadmin/tests -t cueadmin -p "*.py"
pip install -e cueadmin

python -m unittest discover -s cuesubmit/tests -t cuesubmit -p "*.py"
pip install -e cuesubmit
python -m pytest rqd/tests
python -m pytest rqd/pytests

exit
# Xvfb no longer supports Python 2.
if [[ "$python_version" =~ "Python 3" && ${args[0]} != "--no-gui" ]]; then
  ci/run_gui_test.sh
fi
