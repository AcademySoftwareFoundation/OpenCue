#!/usr/bin/env python

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


"""Entrypoint for the CueSubmit application."""


from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
import sys

from qtpy import QtGui
from qtpy import QtWidgets

from cuesubmit import Constants
from cuesubmit import JobTypes
from cuesubmit.ui import Style
from cuesubmit.ui import Submit


class CueSubmitApp(QtWidgets.QApplication):
    """Standalone submission application."""

    def __init__(self, args):
        super(CueSubmitApp, self).__init__(args)
        self.mainWindow = CueSubmitMainWindow(Constants.SUBMIT_APP_WINDOW_TITLE)
        self.icon = QtGui.QPixmap('{}/images/OpenCue.png'.format(Constants.DIR_PATH))
        self.setWindowIcon(self.icon)

    def startup(self):
        """Initializes the application and makes it appear on screen."""
        self.setApplicationName(Constants.SUBMIT_APP_WINDOW_TITLE)
        Style.init()
        self.mainWindow.show()
        self.mainWindow.submitWidget.jobTreeWidget.table.setFocus()


class CueSubmitMainWindow(QtWidgets.QMainWindow):
    """Main Window object for the standalone submission."""

    def __init__(self, name, *args, **kwargs):
        super(CueSubmitMainWindow, self).__init__(*args, **kwargs)
        self.submitWidget = Submit.CueSubmitWidget(
            settingsWidgetType=JobTypes.JobTypes.SHELL,
            parent=self
        )
        self.setCentralWidget(self.submitWidget)
        self.setWindowTitle(name)
        self.setMinimumWidth(650)
        self.resize(self.minimumWidth(), 1050)
        self.setStyleSheet(Style.MAIN_WINDOW)


def main():
    """Entrypoint for the CueSubmit application."""
    app = CueSubmitApp(sys.argv)
    QtGui.qApp = app
    app.startup()
    app.exec_()


if __name__ == '__main__':
    main()
