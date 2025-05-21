#!/bin/bash

set -e

# Install all client packages.
if [[ -v OPENCUE_PROTO_PACKAGE_PATH ]]
then
  echo "Installing pre-built cuebot package"
  pip install ${OPENCUE_PROTO_PACKAGE_PATH}
else
  pip install cuebot/
fi
pip install pycue/ pyoutline/ cueadmin/ cuesubmit/ cuegui/
