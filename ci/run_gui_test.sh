#!/bin/bash

# Wrapper script for CueGUI tests.
#
# xvfb-run sometimes crashes on exit, which gives a non-zero exit code even when the tests
# pass. pytest's own exit code is recorded inside the xvfb session and decides the result.

set -eo pipefail

py="$(command -v python3)"
if [[ -z "$py" ]]; then
  py="$(command -v python)"
fi
echo "Using Python binary ${py}"

if [[ -n "${OPENCUE_CUEGUI_PACKAGE_PATH:-}" ]]
then
  echo "Installing pre-built opencue_cuegui package"
  pip install "${OPENCUE_CUEGUI_PACKAGE_PATH}[test]"
else
  pip install ./cuegui[test]
fi

pytest_status="$(mktemp)"

# Fix for debian version of xvfb-run
source /etc/os-release
XVFB_RUN_ARG="-d"
if [[ $ID_LIKE == *debian* ]]
then
  XVFB_RUN_ARG="-a"
fi

xvfb-run $XVFB_RUN_ARG bash -c '"$1" -m pytest cuegui; echo $? > "$2"' _ "${py}" "${pytest_status}" \
  || echo "xvfb-run exited with status $?"

status="$(cat "${pytest_status}")"
if [[ "${status}" != 0 ]]; then
  echo "CueGUI tests failed (pytest exit code: ${status:-none})"
  exit 1
fi
echo "CueGUI tests passed"
