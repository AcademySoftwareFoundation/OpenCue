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


from outline.config import config
from outline.loader import current_outline
from outline.loader import load_json
from outline.loader import load_outline
from outline.loader import Outline
from outline.loader import parse_outline_script
from outline.loader import quick_outline
