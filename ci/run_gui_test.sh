#!/bin/bash

stderr_log="/tmp/stderr.log"
PYTHONPATH=pycue xvfb-run -d python cuegui/setup.py test 2> >(tee ${stderr_log} >&2)

echo "#################"
echo "Done with main test run"
echo "#################"

cat ${stderr_log}

