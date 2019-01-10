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


import logging

import maya.cmds as cmds
import maya.utils
from PySide2 import QtCore, QtWidgets

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
        NUKE: SettingsWidgets.ShellSettings
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
