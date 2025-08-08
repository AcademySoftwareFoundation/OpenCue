#!/bin/bash

# Script to update version information for local development
# Reads OpenCue version from VERSION.in and updates _data/version.yml

# Get the OpenCue version from VERSION.in
OPENCUE_VERSION=$(cat ../VERSION.in | tr -d '\n')

# Get current date
CURRENT_DATE=$(date +'%Y-%m-%d')

# Get git hash (if in a git repo)
GIT_HASH=$(git rev-parse --short HEAD 2>/dev/null || echo "local")

# Update the _data/version.yml file
cat > _data/version.yml <<EOF
# This file is auto-generated - do not edit manually
# Run ./update_version.sh to update from VERSION.in
version: "main"
doc_version: "0.0.1"
opencue_version: "${OPENCUE_VERSION}"
build_date: "${CURRENT_DATE}"
last_commit: "${CURRENT_DATE}"
git_hash: "${GIT_HASH}"
is_preview: false
EOF

echo "Updated version information:"
echo "   OpenCue Version: ${OPENCUE_VERSION}"
echo "   Git Hash: ${GIT_HASH}"
echo "   Date: ${CURRENT_DATE}"