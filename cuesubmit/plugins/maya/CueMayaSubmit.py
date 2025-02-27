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

import glob
import logging
import os
import sys

import maya.cmds as cmds
import maya.utils
from qtpy import QtCore, QtWidgets

# Path where all of the Cue Python libraries and their dependencies are installed.
# The recommended workflow is for this to be a virtual environment, like:
#   CUE_PYTHONPATH = '<path to virtualenv>/lib/python2.7/site-packages'
if 'CUE_PYTHONPATH' in os.environ:
  sys.path.insert(0, os.environ['CUE_PYTHONPATH'])
  # OpenCue Python libraries are distributed wrapped in .egg directories; add
  # those too.
  for egg_dir in glob.glob(os.path.join(os.environ['CUE_PYTHONPATH'], '*.egg')):
    sys.path.append(egg_dir)
  # Maya has trouble importing google.protobuf due to not recognizing the google/
  # directory as a proper module. Forcing creation of an __init__.py fixes this.
  google_dir = os.path.join(os.environ['CUE_PYTHONPATH'], 'google')
  if os.path.isdir(google_dir):
    google_init = os.path.join(google_dir, '__init__.py')
    if not os.path.exists(google_init):
      open(google_init, 'a').close()

# Infer the path to the current CueSubmit install and add that to the path as well,
# since it might not be included in the same places as the library installs.
sys.path.insert(0,
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))))

from cuesubmit import Constants
from cuesubmit import JobTypes
from cuesubmit.ui import SettingsWidgets
from cuesubmit.ui import Style
from cuesubmit.ui import Submit

log = logging.getLogger(Constants.UI_NAME)
window = None


class MayaJobTypes(JobTypes.JobTypes):
    SHELL = 'Shell'
    MAYA = 'Maya'
    NUKE = 'Nuke'

    SETTINGS_MAP = {
        SHELL: SettingsWidgets.ShellSettings,
        MAYA: SettingsWidgets.InMayaSettings,
        NUKE: SettingsWidgets.BaseNukeSettings
    }

    def __init__(self):
        super(MayaJobTypes, self).__init__()


class CueSubmitMainWindow(QtWidgets.QMainWindow):
    """Main Window object for the standalone submission"""

    def __init__(self, name, *args, **kwargs):
        super(CueSubmitMainWindow, self).__init__(*args, **kwargs)
        self.setWindowFlags(QtCore.Qt.Window)
        self.setProperty('saveWindowPref', True)
        self.submitWidget = Submit.CueSubmitWidget(
            jobTypes=MayaJobTypes,
            settingsWidgetType=MayaJobTypes.MAYA,
            filename=getFilename(),
            cameras=getCameras(),
            parent=self
        )
        self.setStyleSheet(Style.MAIN_WINDOW)
        self.setCentralWidget(self.submitWidget)
        self.setWindowTitle(name)
        self.setMinimumWidth(650)
        self.resize(self.minimumWidth(), 1000)


def getFilename():
    """Return the current Maya scene filename."""
    return cmds.file(q=True, sn=True)


def getCameras():
    """Return a list of cameras in the current maya scene."""
    return cmds.listRelatives(cmds.ls(type='camera'), p=True)


def delete_existing_ui():
    """Delete the existing ui before we launch a new one"""
    control_name = Constants.UI_NAME + 'WorkspaceControl'
    if cmds.workspaceControl(control_name, q=True, exists=True):
        cmds.workspaceControl(control_name, e=True, close=True)
        cmds.deleteUI(control_name, control=True)


def setupLogging():
    """Enable logging."""
    if not log.handlers:
        log.propagate = False
        handler = maya.utils.MayaGuiLogHandler()
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s [%(name)s] - %(message)s')
        handler.setFormatter(formatter)
        log.addHandler(handler)


def main():
    global window
    delete_existing_ui()
    window = CueSubmitMainWindow('Submit to OpenCue')
    window.show()
