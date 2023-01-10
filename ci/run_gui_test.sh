#!/bin/bash

test_log="/tmp/cuegui_result.log"
PYTHONPATH=pycue xvfb-run -d python cuegui/setup.py test | tee ${test_log}

echo "#################"
echo "Done with main test run"
echo "#################"


#ls -l ${test_log}
#cat ${test_log}

echo "grep"
grep -Pzl 'Ran \d+ tests in [0-9\.]+s\n\nOK' ${test_log}

echo "pcregrep"
pcregrep -M 'Ran \d+ tests in [0-9\.]+s\n\nOK' ${test_log}
