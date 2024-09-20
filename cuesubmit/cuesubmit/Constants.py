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


"""Constants used throughout the code.

Some values can be overridden by custom config, see Config.py."""

from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
import os

from cuesubmit import Config

config = Config.getConfigValues()

UP_KEY = 16777235
DOWN_KEY = 16777237
TAB_KEY = 16777217

UI_NAME = config.get('UI_NAME', 'OPENCUESUBMIT')
SUBMIT_APP_WINDOW_TITLE = config.get('SUBMIT_APP_WINDOW_TITLE', 'OpenCue Submit')

MAYA_RENDER_CMD = config.get('MAYA_RENDER_CMD', 'Render')
NUKE_RENDER_CMD = config.get('NUKE_RENDER_CMD', 'nuke')
BLENDER_RENDER_CMD = config.get('BLENDER_RENDER_CMD', 'blender')
RENDER_CMDS = config.get('RENDER_CMDS', {})

DEFAULT_SHOW = config.get('DEFAULT_SHOW') or os.environ.get('PROJECT', 'default')

FRAME_TOKEN = config.get('FRAME_TOKEN', '#IFRAME#')
FRAME_START_TOKEN = config.get('FRAME_START', '#FRAME_START#')
FRAME_END_TOKEN = config.get('FRAME_END', '#FRAME_END#')

# Tokens are replaced by cuebot during dispatch with their computed value.
# see: cuebot/src/main/java/com/imageworks/spcue/dispatcher/DispatchSupportService.java
# Update this file when updating tokens in cuebot, they will appear in the cuesubmit tooltip popup.
COMMAND_TOKENS = {'#ZFRAME#': 'Current frame with a padding of 4',
                  '#IFRAME#': 'Current frame',
                  '#FRAME_START#': 'First frame of chunk',
                  '#FRAME_END#': 'Last frame of chunk',
                  '#FRAME_CHUNK#': 'Chunk size',
                  '#FRAMESPEC#': 'Full frame range',
                  '#LAYER#': 'Name of the Layer',
                  '#JOB#': 'Name of the Job',
                  '#FRAME#': 'Name of the Frame'
                  }

MAYA_FILE_FILTERS = [
    'Maya Ascii file (*.ma)',
    'Maya Binary file (*.mb)',
    'Maya file (*.ma *.mb)'
]
NUKE_FILE_FILTERS = ['Nuke script file (*.nk)']
BLENDER_FILE_FILTERS = ['Blender file (*.blend)']


BLENDER_FORMATS = ['', 'AVIJPEG', 'AVIRAW', 'BMP', 'CINEON', 'DPX', 'EXR', 'HDR', 'IRIS', 'IRIZ',
                   'JP2', 'JPEG', 'MPEG', 'MULTILAYER', 'PNG', 'RAWTGA', 'TGA', 'TIFF']
BLENDER_OUTPUT_OPTIONS_URL = \
    'https://docs.blender.org/manual/en/latest/advanced/command_line/arguments.html#render-options'

REGEX_CUETOKEN = r'^#.*#$' #FRAME_START#
REGEX_COMMAND_OPTIONS = (r'(?P<command_flag>-+\w*)?'   # -optionFlag
                         r'(?P<hidden>\~)?'            # -hiddenFlag~
                         r'\s?'
                         r'({'
                           r'(?P<mandatory>\!)?'      # {!Mandatory argument}
                           r'(?P<label>[^{}\*\/\!]+)' # {Nice name}
                           r'(?P<browsable>\*?\/?)'   # {browseFile*} or {browseFolder/}
                         r'})?')

DIR_PATH = os.path.dirname(__file__)

# Dropdown label to specify the default Facility, i.e. let Cuebot decide.
DEFAULT_FACILITY_TEXT = '[Default]'
