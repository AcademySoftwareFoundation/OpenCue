#!/bin/bash

python -m pip install licensecheck==2026.0.8

licensecheck --requirements-paths */pyproject.toml --ignore-package opencue-* --zero
