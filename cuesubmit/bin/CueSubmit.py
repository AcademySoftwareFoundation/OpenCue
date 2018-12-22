#!/usr/bin/env python

import sys

from PySide2 import QtWidgets

from cuesubmit import Constants
from cuesubmit import JobTypes
from cuesubmit.ui import Style
from cuesubmit.ui import Submit


class CueSubmitApp(QtWidgets.QApplication):
    """Standalone submission application"""

    def __init__(self, args):
        super(CueSubmitApp, self).__init__(args)
        self.mainWindow = CueSubmitMainWindow(Constants.SUBMIT_APP_WINDOW_TITLE)

    def startup(self):
        self.setApplicationName(Constants.SUBMIT_APP_WINDOW_TITLE)
        Style.init()
        self.mainWindow.show()
        self.mainWindow.submitWidget.jobTreeWidget.table.setFocus()


class CueSubmitMainWindow(QtWidgets.QMainWindow):
    """Main Window object for the standalone submission"""

    def __init__(self, name, *args, **kwargs):
        super(CueSubmitMainWindow, self).__init__(*args, **kwargs)
        self.submitWidget = Submit.CueSubmitWidget(
            settingsWidgetType=JobTypes.JobTypes.SHELL,
            parent=self
        )
        self.setCentralWidget(self.submitWidget)
        self.setWindowTitle(name)
        self.setMinimumWidth(650)
        self.setStyleSheet(Style.MAIN_WINDOW)


def main():
    app = CueSubmitApp(sys.argv)
    app.startup()
    app.exec_()


if __name__ == '__main__':
    main()
