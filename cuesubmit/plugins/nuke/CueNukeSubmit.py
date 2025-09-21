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

import argparse
import logging

from qtpy import QtCore, QtWidgets

from cuesubmit import Constants
from cuesubmit import JobTypes
from cuesubmit.ui import SettingsWidgets
from cuesubmit.ui import Style
from cuesubmit.ui import Submit

log = logging.getLogger(Constants.UI_NAME)
window = None
NUKE_WINDOW_TITLE = 'Submit to OpenCue'


class NukeJobTypes(JobTypes.JobTypes):
    SHELL = 'Shell'
    MAYA = 'Maya'
    NUKE = 'Nuke'

    SETTINGS_MAP = {
        SHELL: SettingsWidgets.ShellSettings,
        MAYA: SettingsWidgets.BaseMayaSettings,
        NUKE: SettingsWidgets.InNukeSettings
    }

    def __init__(self):
        super(NukeJobTypes, self).__init__()


class CueSubmitNukeWindow(QtWidgets.QMainWindow):
    """Main Window object for the Nuke submission"""

    def __init__(self, name, filename=None, writeNodes=None):
        super(CueSubmitNukeWindow, self).__init__()
        self.setWindowFlags(QtCore.Qt.Window)
        self.setProperty('saveWindowPref', True)
        self.submitWidget = Submit.CueSubmitWidget(
            jobTypes=NukeJobTypes,
            settingsWidgetType=NukeJobTypes.NUKE,
            filename=filename,
            writeNodes=writeNodes,
            parent=self
        )
        self.setStyleSheet(Style.MAIN_WINDOW)
        self.setCentralWidget(self.submitWidget)
        self.setWindowTitle(name)
        self.setMinimumWidth(650)
        self.resize(self.minimumWidth(), 1000)


class CueSubmitNukeApp(QtWidgets.QApplication):
    """Application object for the Nuke submitter. Runs outside of Nuke."""

    def __init__(self, nukeFile, writeNodes):
        super(CueSubmitNukeApp, self).__init__()
        self.mainWindow = CueSubmitNukeWindow(NUKE_WINDOW_TITLE, filename=nukeFile,
                                              writeNodes=writeNodes)

    def startup(self):
        self.setApplicationName(Constants.SUBMIT_APP_WINDOW_TITLE)
        Style.init()
        self.mainWindow.show()
        self.mainWindow.submitWidget.jobTreeWidget.table.setFocus()


def main(nukeFile, writeNodes):
    """Main entrypoint for launching the QApp.
    @type: nukeFile: str
    @param: nukeFile: path to the nuke file
    @type: writeNodes: list<string>
    @param: List of Write nodes to execute. Empty means execute all.
    """
    app = CueSubmitNukeApp(nukeFile, writeNodes)
    app.startup()
    app.exec_()


def parseArgs():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", help="File path to Nuke scene file.")
    parser.add_argument("--nodes", nargs='*', help="Names of write nodes to execute."
                                                   "If none, execute all.")
    return parser.parse_args()


if __name__ == '__main__':
    args = parseArgs()
    main(args.file, args.nodes)
