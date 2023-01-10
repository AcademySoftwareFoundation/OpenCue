#!/bin/bash

test_log="/tmp/cuegui_result.log"
PYTHONPATH=pycue xvfb-run -d python cuegui/setup.py test | tee ${test_log}

echo "#################"
echo "Done with main test run"
echo "#################"

echo "grep"
grep -Pz 'Ran \d+ tests in [0-9\.]+s\n\nOK' ${test_log}
if [ $? -eq 0 ]; then
  echo "Detected passing tests"
  exit 0
fi

echo "Detected test failure"
exit 1
