#!/bin/bash

set -e

# Requirements for running the tests on the vfx-platform images
python -m pip install coverage pytest-xvfb

pip install ./proto[test] \
            ./pycue[test] \
            ./pyoutline[test] \
            ./cueadmin[test] \
            ./cueman[test] \
            ./cuegui[test] \
            ./cuesubmit[test]

# Run coverage for each component individually, but append it all into the same report.
python -m coverage run -m pytest ./pycue
python -m coverage  run -m pytest ./pyoutline
python -m coverage  run -m pytest ./cueadmin
python -m coverage  run -m pytest ./cueman
python -m coverage  run -m pytest ./cuesubmit
# TODO: re-enable cuegui tests when xvfb-run gets configured to execute on the new vfx-platform
# python -m coverage  run -m pytest ./cuegui

# SonarCloud needs the report in XML.
python -m coverage xml
