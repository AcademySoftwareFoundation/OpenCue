#!/bin/bash

# Wrapper script for CueGUI tests.
#
# xvfb-run sometimes crashes on exit, we haven't been able to figure out why yet.
# This means that tests may pass but the xvfb-run crash will generate a non-zero exit code
# and cause our CI pipeline to fail.
#
# We work around this by capturing unit test output and looking for the text that indicates
# tests have passed:
#
# > Ran 209 tests in 4.394s
# >
# > OK
#

py="$(command -v python3)"
if [[ -z "$py" ]]; then
  py="$(command -v python)"
fi
echo "Using Python binary ${py}"

if [[ -v OPENCUE_CUEGUI_PACKAGE_PATH ]]
then
  echo "Installing pre-built opencue_cuegui package"
  pip install "${OPENCUE_CUEGUI_PACKAGE_PATH}[test]"
else
  pip install ./cuegui[test]
fi

test_log="/tmp/cuegui_result.log"

# Fix for debian version of xvfb-run
source /etc/os-release
XVFB_RUN_ARG="-d"
if [[ $ID_LIKE == *debian* ]]
then
  XVFB_RUN_ARG="-a"
fi

xvfb-run $XVFB_RUN_ARG "${py}" -m pytest cuegui| tee ${test_log}

grep -Pz '\d+ failed' ${test_log}
if [ $? -eq 1 ]; then
  echo "Detected passing tests"
  exit 0
fi

echo "Detected test failure"
exit 1
