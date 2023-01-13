#!/bin/bash

curl -s https://api.github.com/repos/AcademySoftwareFoundation/OpenCue/releases/latest \
  | grep tag_name \
  | cut -d \" -f 4 \
  | tr -d v
