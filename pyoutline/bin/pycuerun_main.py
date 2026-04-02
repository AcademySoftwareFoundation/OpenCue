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

"""Console script entry point for pycuerun."""

import importlib.machinery
import importlib.util
import os
import sys

# Add the bin directory to sys.path so that 'from cuerunbase import AbstractCuerun'
# works when the pycuerun script is loaded.
sys.path.insert(0, os.path.dirname(__file__))

# Load bin/pycuerun (which has no .py extension) using importlib.
# We must provide a SourceFileLoader explicitly because spec_from_file_location
# returns None for files without a .py extension.
_script_path = os.path.join(os.path.dirname(__file__), "pycuerun")
_loader = importlib.machinery.SourceFileLoader("pycuerun", _script_path)
_spec = importlib.util.spec_from_file_location("pycuerun", _script_path, loader=_loader)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)


def main():
    _mod.PyCuerun().go()
