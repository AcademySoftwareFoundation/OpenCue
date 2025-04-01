#!/bin/bash

set -e

# Install all client packages.
if [[ -v CUBOT_PACKAGE_PATH ]]
then
  echo "Installing pre-built cuebot package"
  pip install ${CUBOT_PACKAGE_PATH}
else
  pip install cuebot/
fi
pip install pycue/ pyoutline/ cueadmin/ cuesubmit/ cuegui/
