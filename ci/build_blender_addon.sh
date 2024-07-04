#!/bin/bash
#  Copyright Contributors to the OpenCue Project
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

# OpenCue integration test script
#
# Stands up a clean environment using Docker compose and verifies all
# components are functioning as expected.
#
# Run with:
#   ./build_blender_addon.sh

set -e

PYOUTLINE_PATH="pyoutline/outline"
FILESEQUENCE_PATH="pycue/FileSequence"
OPENCUE_PATH="pycue/opencue"

ADDON_PATH="cuesubmit/plugins/blender/OpenCue-Blender"

log() {
    echo "$(date "+%Y-%m-%d %H:%M:%S") $1 $2"
}

copy_dependencies() {
  DEPENDENCIES_PATH="${ADDON_PATH}/dependencies"
  mkdir -p "${DEPENDENCIES_PATH}"
  cp -r "${PYOUTLINE_PATH}" "${DEPENDENCIES_PATH}"
  cp -r "${FILESEQUENCE_PATH}" "${DEPENDENCIES_PATH}"
  cp -r "${OPENCUE_PATH}" "${DEPENDENCIES_PATH}"
}

main() {
  log INFO "Copying dependencies into ${ADDON_PATH}"
  copy_dependencies
  # Check if script is running within GitHub Actions pipeline
  if ["$GITHUB_ACTIONS" == "true"]
  then
    mkdir -p "${GITHUB_WORKSPACE}/artifacts/"
    zip -r "${GITHUB_WORKSPACE}/artifacts/OpenCue-Blender.zip" "${ADDON_PATH}"
  else
    zip -r "cuesubmit/plugins/blender/OpenCue-Blender.zip" "${ADDON_PATH}"
  fi
}