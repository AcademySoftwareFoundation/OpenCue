#!/bin/bash

set -e

# Sphinx has some additional requirements
pip install --user -r requirements.txt -r api_docs/requirements.txt

ci/build_proto.sh

# Build the docs and treat warnings as errors
~/.local/bin/sphinx-build -W -b html -d api_docs/_build/doctrees api_docs api_docs/_build/html
