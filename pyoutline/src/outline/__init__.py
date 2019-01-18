#  Copyright (c) 2018 Sony Pictures Imageworks Inc.
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


"""Outline is a library for scripting shell commands to
be executed over a frame range.  Typically these shell
commands would be executed in parallel on a render farm.
"""

import os
import sys

# PyOutline requires Python 2.5
if sys.version_info[:2][1] < 5:
    raise Exception("Pyoutline requires Python 2.5 or greater.")

# Make sure we are in a setshot shell.
try:
    os.environ["SHOW"]
except:
    raise Exception("You must set the SHOW env var to use pyoutline.")

from outline.config import config

from outline.exception import *

from outline.loader import *

from outline.session import *

from outline.executor import *

import outline.io as io

from outline.layer import *

import outline.cuerun as cuerun

from outline.plugins import PluginManager
