#!/bin/bash

test_log="/tmp/cuegui_result.log"
PYTHONPATH=pycue xvfb-run -d python cuegui/setup.py test | tee ${test_log}

echo "#################"
echo "Done with main test run"
echo "#################"

ls -l ${test_log}
cat ${test_log}

