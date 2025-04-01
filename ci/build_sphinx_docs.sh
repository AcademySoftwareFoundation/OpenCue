#!/bin/bash

set -e

if [[ -v VIRTUAL_ENV ]]
then
  PIP_OPT=""
else
  PIP_OPT="--user"
fi

# Sphinx has some additional requirements
pip install ${PIP_OPT} -r api_docs/requirements.txt

pip install ${PIP_OPT} cuebot/ pycue/ pyoutline/ cueadmin/ cuesubmit/ cuegui/
# ci/build_proto.sh

# Build the docs and treat warnings as errors
sphinx-build -W -b html -d api_docs/_build/doctrees api_docs api_docs/_build/html
