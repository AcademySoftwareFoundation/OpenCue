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


"""
Outline is a library for scripting shell commands to be executed over a frame range.  Typically
these shell commands would be executed in parallel on a render farm.
"""


from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

# pylint: disable=cyclic-import,redefined-builtin

from .config import config
from .exception import *
from .loader import *
from .session import *
from .executor import *
from . import io
from .layer import *
from . import cuerun
from .plugins import PluginManager
