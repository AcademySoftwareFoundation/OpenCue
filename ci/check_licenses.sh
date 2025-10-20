#!/bin/bash

python -m pip install licensecheck==2025.1.0

licensecheck --requirements-paths */pyproject.toml --ignore-package opencue-* --zero
