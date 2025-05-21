#!/bin/bash

set -e

# Install all client packages.
if [[ -n "${OPENCUE_PROTO_PACKAGE_PATH+x}" ]]
then
  echo "Installing pre-built cuebot package"
  pip install ${OPENCUE_PROTO_PACKAGE_PATH}
fi
pip install pycue pyoutline cueadmin cuesubmit cuegui
