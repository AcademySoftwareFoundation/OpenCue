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

test_log="/tmp/cuegui_result.log"
PYTHONPATH=pycue xvfb-run -d "${py}" -m unittest discover -s cuegui/tests -t cuegui -p "*.py"| tee ${test_log}

grep -Pz 'Ran \d+ tests in [0-9\.]+s\n\nOK' ${test_log}
if [ $? -eq 0 ]; then
  echo "Detected passing tests"
  exit 0
fi

echo "Detected test failure"
exit 1
