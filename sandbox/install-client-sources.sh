#!/bin/bash

# Installs OpenCue Python client libraries from source.
#
# Read the [OpenCue sandbox documentation](https://github.com/AcademySoftwareFoundation/OpenCue/blob/master/sandbox/README.md)
# to learn how to set up a local OpenCue environment.

# This script should be run from the root of the OpenCue repository.

set -e

# Install all client packages.
if [[ -n "${OPENCUE_PROTO_PACKAGE_PATH+x}" ]]
then
  echo "Installing pre-built cuebot package"
  pip install ${OPENCUE_PROTO_PACKAGE_PATH}
else
  VERSION_TAG="$(cat VERSION.in | tr -d '[:space:]')"
  # Check if the tag already exists
  if git tag --list "$VERSION_TAG" | grep -q "^$VERSION_TAG$"; then
    echo "Tag $VERSION_TAG already exists."
  else
    echo "Creating tag $VERSION_TAG"
    git tag "$VERSION_TAG"
  fi
  # Build the proto package
  pip install proto/
fi
pip install pycue/ pyoutline/ cueadmin/ cuesubmit/ cuegui/
