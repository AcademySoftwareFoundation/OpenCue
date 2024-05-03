#!/bin/bash

# Script for fetching the latest release version of OpenCue.
# - `curl` fetches all of the metadata for the latest release, in JSON format.
# - `grep` filters for just the `"tag_name": "v1.2.3"` line.
# - `cut` extracts the `v1.2.3` value from the `tag_name` line.
# - `tr` removes the `v` to leave us with the final version number e.g. `1.2.3`.

curl -s https://api.github.com/repos/AcademySoftwareFoundation/OpenCue/releases/latest \
  | grep tag_name \
  | cut -d \" -f 4 \
  | tr -d v
