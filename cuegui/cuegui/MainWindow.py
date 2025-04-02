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


"""The main window of the application. Multiple windows may exist.

All CueGUI windows are an instance of this MainWindow."""


from __future__ import absolute_import
from __future__ import print_function
from __future__ import division


from builtins import str
from builtins import range

import os
import sys
import time
import yaml

from qtpy import QtCore
from qtpy import QtGui
from qtpy import QtWidgets

import opencue

import cuegui.Constants
import cuegui.Logger
import cuegui.Plugins
import cuegui.Utils


logger = cuegui.Logger.getLogger(__file__)


class MainWindow(QtWidgets.QMainWindow):
    """The main window of the application. Multiple windows may exist."""

    # Message to be displayed when a change requires an application restart
    USER_CONFIRM_RESTART = "You must restart for this action to take effect, close window?: "

    windows = []
    windows_names = []
    windows_titles = {}
    windows_actions = {}

    def __init__(self, app_name, app_version, window_name, parent = None):
        QtWidgets.QMainWindow.__init__(self, parent)
        self.app = cuegui.app()

        self.__actions_facility = {}
        self.facility_default = None
        self.facility_dict = None
        self.windowMenu = None

        self.settings = self.app.settings
        self.windows_names = [app_name] + ["%s_%s" % (app_name, num) for num in range(2, 5)]
        self.app_name = app_name
        self.app_version = app_version
        if window_name:
            self.name = window_name
        else:
            self.name = self.windows_names[0]
        self.__isEnabled = yaml.safe_load(self.app.settings.value("EnableJobInteraction", "False"))

        # Provides a location for widgets to the right of the menu
        menuLayout = QtWidgets.QHBoxLayout()
        menuLayout.addStretch()
        self.menuBar().setLayout(menuLayout)

        # Configure window
        self.setMinimumSize(600, 400)
        self.setAnimated(False)
        self.setDockNestingEnabled(True)

        # Create checkable menuitem
        self.saveWindowSettingsCheck = QtWidgets.QAction("Save Window Settings on Exit", self)
        self.saveWindowSettingsCheck.setCheckable(True)

        # Register this window
        self.__windowOpened()

        # Create menus
        self.__createMenus()

        # Setup plugins
        # pylint: disable=no-member
        self.__plugins = cuegui.Plugins.Plugins(self, self.name)
        # pylint: enable=no-member
        self.__plugins.setupPluginMenu(self.PluginMenu)

        # Restore saved settings
        self.__restoreSettings()

        self.app.status.connect(self.showStatusBarMessage)
        self.showStatusBarMessage("Ready")

    def displayStartupNotice(self):
        """Displays the application startup notice."""
        now = int(time.time())
        lastView = int(self.settings.value("LastNotice", 0))
        if lastView < cuegui.Constants.STARTUP_NOTICE_DATE:
            QtWidgets.QMessageBox.information(self, "Notice", cuegui.Constants.STARTUP_NOTICE_MSG,
                                              QtWidgets.QMessageBox.Ok)
        self.settings.setValue("LastNotice", now)

    def showStatusBarMessage(self, message, delay=5000):
        """Shows a message on the status bar."""
        self.statusBar().showMessage(str(message), delay)

    def displayAbout(self):
        """Displays about text."""
        msg = f"{self.app_name}\n\nA opencue tool\n\n"
        msg += f"CueGUI:\n{cuegui.Constants.VERSION}\n\n"

        # Only show the labels (Beta or Stable) if OPENCUE_BETA exists
        opencue_beta = os.getenv('OPENCUE_BETA')
        if opencue_beta:
            if opencue_beta == '1':
                msg += "(Beta Version)\n\n"
            else:
                msg += "(Stable Version)\n\n"

        msg += f"Qt:\n{QtCore.qVersion()}\n\n"
        msg += f"Python:\n{sys.version}\n\n"
        QtWidgets.QMessageBox.about(self, "About", msg)

    def handleExit(self, sig, flag):
        """Save current state and close the application"""
        del sig
        del flag
        # Only save settings on exit if toggled
        if self.saveWindowSettingsCheck.isChecked():
            self.__saveSettings()
        self.__windowCloseApplication()

    @staticmethod
    def openSuggestionPage():
        """Opens the suggestion page URL."""
        cuegui.Utils.openURL(cuegui.Constants.URL_SUGGESTION)

    @staticmethod
    def openBugPage():
        """Opens the bug report page."""
        cuegui.Utils.openURL(cuegui.Constants.URL_BUG)

    @staticmethod
    def openUserGuide():
        """Opens the user guide page."""
        cuegui.Utils.openURL(cuegui.Constants.URL_USERGUIDE)

    ################################################################################
    # Handles facility menu
    ################################################################################

    def __facilityMenuSetup(self, menu):
        """Creates the facility menu actions
        @param menu: The QMenu that the actions should be added to
        @type  menu: QMenu
        @return: The QMenu that the actions were added to
        @rtype:  QMenu"""
        self.__actions_facility = {}
        menu.setFont(cuegui.Constants.STANDARD_FONT)
        menu.triggered.connect(self.__facilityMenuHandle)

        cue_config = opencue.Cuebot.getConfig()
        self.facility_default = os.getenv(
            "CUEBOT_FACILITY",
            cue_config.get("cuebot.facility_default"))
        self.facility_dict = cue_config.get("cuebot.facility")

        for facility in self.facility_dict:
            self.__actions_facility[facility] = QtWidgets.QAction(facility, menu)
            self.__actions_facility[facility].setCheckable(True)
            menu.addAction(self.__actions_facility[facility])

        self.__actions_facility[self.facility_default].setChecked(True)
        return menu

    def __facilityMenuHandle(self, action):
        """Called when a facility menu item is clicked on.
        @param action: Menu QAction
        @type  action: QAction"""
        # If all cues are unchecked, check default one
        if not action.isChecked():
            checked = False
            for facility in list(self.__actions_facility.values()):
                if facility.isChecked():
                    checked = True
            if not checked:
                self.__actions_facility[self.facility_default].setChecked(True)
        # Uncheck all other facilities if one is checked
        else:
            for facility, facvalue in self.__actions_facility.items():
                if facility != action.text():
                    facvalue.setChecked(False)

        for facility in list(self.__actions_facility.values()):
            if facility.isChecked():
                opencue.Cuebot.setHostWithFacility(str(facility.text()))
                self.app.facility_changed.emit()
                return

    ################################################################################

    def __createMenus(self):
        """Creates the menus at the top of the window"""
        self.menuBar().setFont(cuegui.Constants.STANDARD_FONT)

        # Menu bar
        self.fileMenu = self.menuBar().addMenu("&File")
        self.facilityMenu = self.__facilityMenuSetup(self.menuBar().addMenu("&Cuebot Facility"))
        self.PluginMenu = self.menuBar().addMenu("&Views/Plugins")
        self.windowMenu = self.menuBar().addMenu("&Window")
        self.helpMenu = self.menuBar().addMenu("&Help")

        if self.__isEnabled is False:
            # Menu Bar: File -> Enable Job Interaction
            enableJobInteraction = QtWidgets.QAction(QtGui.QIcon('icons/exit.png'),
                                                     '&Enable Job Interaction', self)
            enableJobInteraction.setStatusTip('Enable Job Interaction')
            enableJobInteraction.triggered.connect(self.__enableJobInteraction)
            self.fileMenu.addAction(enableJobInteraction)
        # allow user to disable the job interaction
        else:
            # Menu Bar: File -> Disable Job Interaction
            enableJobInteraction = QtWidgets.QAction(QtGui.QIcon('icons/exit.png'),
                                                     '&Disable Job Interaction', self)
            enableJobInteraction.setStatusTip('Disable Job Interaction')
            enableJobInteraction.triggered.connect(self.__enableJobInteraction)
            self.fileMenu.addAction(enableJobInteraction)

        # Menu Bar: File -> Close Window
        close = QtWidgets.QAction(QtGui.QIcon('icons/exit.png'), '&Close Window', self)
        close.setStatusTip('Close Window')
        close.triggered.connect(self.__windowCloseWindow)  # pylint: disable=no-member
        self.fileMenu.addAction(close)

        # Menu Bar: File -> Exit Application
        exitAction = QtWidgets.QAction(QtGui.QIcon('icons/exit.png'), 'E&xit Application', self)
        exitAction.setShortcut('Ctrl+Q')
        exitAction.setStatusTip('Exit application')
        exitAction.triggered.connect(self.__windowCloseApplication)  # pylint: disable=no-member
        self.fileMenu.addAction(exitAction)

        self.__windowMenuSetup(self.windowMenu)

        self.windowMenu.addSeparator()

        self.__toggleFullscreenSetup(self.windowMenu)

        # Menu Bar: Help -> Online User Guide.
        action = QtWidgets.QAction('Online User Guide', self)
        action.triggered.connect(self.openUserGuide)  # pylint: disable=no-member
        self.helpMenu.addAction(action)

        # Menu Bar: Help -> Make a Suggestion
        action = QtWidgets.QAction('Make a Suggestion', self)
        action.triggered.connect(self.openSuggestionPage)  # pylint: disable=no-member
        self.helpMenu.addAction(action)

        # Menu Bar: Help -> Report a Bug
        action = QtWidgets.QAction('Report a Bug', self)
        action.triggered.connect(self.openBugPage)  # pylint: disable=no-member
        self.helpMenu.addAction(action)

        self.helpMenu.addSeparator()

        # Menu Bar: Help -> About
        about = QtWidgets.QAction(QtGui.QIcon('icons/about.png'), 'About', self)
        about.setShortcut('F1')
        about.setStatusTip('About')
        about.triggered.connect(self.displayAbout)  # pylint: disable=no-member
        self.helpMenu.addAction(about)

    ################################################################################
    # Handles adding windows
    ################################################################################

    def __windowMenuSetup(self, menu):
        """Creates the menu items for dealing with multiple main windows"""
        self.windowMenu = menu

        # Menu Bar: Window -> Change Window Title
        changeTitle = QtWidgets.QAction("Change Window Title", self)
        changeTitle.triggered.connect(self.__windowMenuHandleChangeTitle)  # pylint: disable=no-member
        menu.addAction(changeTitle)

        # Menu Bar: Window -> Save Window Settings on Exit
        self.saveWindowSettingsCheck.triggered.connect(self.__saveSettingsToggle)  # pylint: disable=no-member
        menu.addAction(self.saveWindowSettingsCheck)

        # Menu Bar: Window -> Save Window Settings
        saveWindowSettings = QtWidgets.QAction("Save Window Settings", self)
        saveWindowSettings.triggered.connect(self.__saveSettings)  # pylint: disable=no-member
        menu.addAction(saveWindowSettings)

        # Menu Bar: Window -> Revert To Default Window Layout
        revertWindowSettings = QtWidgets.QAction("Revert To Default Window Layout", self)
        revertWindowSettings.triggered.connect(self.__revertLayout)  # pylint: disable=no-member
        menu.addAction(revertWindowSettings)

        menu.addSeparator()

        # Load list of window titles
        if not self.windows_titles:
            for name in self.windows_names:
                self.windows_titles[name] = str(self.settings.value("%s/Title" % name, name))

        # Create menu items for Window -> Open/Raise/Add Window "?"
        for name in self.windows_names:
            if name not in self.windows_actions:
                self.windows_actions[name] = QtWidgets.QAction("", self)

            menu.addAction(self.windows_actions[name])

        self.windowMenu.triggered.connect(self.__windowMenuHandle)

        self.__windowMenuUpdate()

    def __windowMenuUpdate(self):
        """Updates the QAction for each main window"""
        number = 1
        for name in self.windows_names:
            title = self.settings.value("%s/Title" % name, "")
            if title:
                title = "Open Window: %s" % self.windows_titles[name]
            else:
                title = "(%s) Add new window" % number
            self.windows_actions[name].setText(title)
            number += 1

        # Rename all the window menu actions to the window title
        for window in self.windows:
            self.windows_actions[window.name].setText("Raise Window: %s" % window.windowTitle())

    def __windowMenuHandle(self, action):
        """Handles the proper action for when a main window's QAction is clicked"""
        action_title = str(action.text())
        if action_title.startswith("Open Window: "):
            window_title = action_title.replace("Open Window: ","")
            # pylint: disable=consider-using-dict-items
            for name in self.windows_titles:
                if self.windows_titles[name] == window_title:
                    self.windowMenuOpenWindow(name)

        elif action_title.endswith("Add new window") and len(action_title) == 18:
            number = int(action_title[1:].split(")", maxsplit=1)[0]) - 1
            self.windowMenuOpenWindow(self.windows_names[number])

        elif action_title.startswith("Raise Window: "):
            for window in self.windows:
                if str(window.windowTitle()) == action_title.replace("Raise Window: ",""):
                    window.raise_()
                    return

    def __windowMenuHandleChangeTitle(self):
        """Changes the title of the current window"""
        # Change the title of the current window
        (value, choice) = QtWidgets.QInputDialog.getText(
            self, "Rename window","Please provide a title for the window",
            QtWidgets.QLineEdit.Normal, str(self.windowTitle()))
        if choice:
            # Don't allow the same name twice
            for window in self.windows:
                if window.name == str(value) or str(window.windowTitle()) == str(value):
                    return
            self.setWindowTitle(str(value))
            self.windows_titles[self.name] = str(value)

        # Save the new title to settings
        self.settings.setValue("%s/Title" % self.name, self.windowTitle())

        self.__windowMenuUpdate()

    def windowMenuOpenWindow(self, name):
        """Launches the desired window"""
        # Don't open the same window twice
        for window in self.windows:
            if window.name == name or str(window.windowTitle()) == name:
                window.raise_()
                return

        # Create the new window
        mainWindow = MainWindow(self.app_name, self.app_version, name)
        if str(mainWindow.windowTitle()) == self.app_name:
            mainWindow.setWindowTitle(name)
        mainWindow.show()
        mainWindow.raise_()

        self.__windowMenuUpdate()

    def __windowOpened(self):
        """Called from __init__ on window creation"""
        self.app.quit.connect(self.close)
        self.windows.append(self)
        self.app.closingApp = False

    def __windowClosed(self):
        """Called from closeEvent on window close"""

        # pylint: disable=bare-except
        try:
            self.windows.remove(self)
        except:
            pass
        self.__windowMenuUpdate()

    def __windowCloseWindow(self):
        """Closes the current window"""
        self.close()

    def __windowCloseApplication(self):
        """Called when the entire application should exit. Signals other windows
        to exit."""
        self.app.closingApp = True
        self.app.quit.emit()
        # Give the application some time to save the state
        time.sleep(4)

    ################################################################################

    def __toggleFullscreenSetup(self, menu):
        # Menu Bar: Window -> Toggle Full-Screen
        fullscreen = QtWidgets.QAction(
            QtGui.QIcon('icons/fullscreen.png'), 'Toggle Full-Screen', self)
        fullscreen.setShortcut('Ctrl+F')
        fullscreen.setStatusTip('Toggle Full-Screen')
        fullscreen.triggered.connect(self.__toggleFullscreen)  # pylint: disable=no-member
        menu.addAction(fullscreen)

    def __toggleFullscreen(self):
        """Toggles the window state between fullscreen and maximized"""
        if self.isFullScreen():
            self.showNormal()
            self.showMaximized()
        else:
            self.showFullScreen()

    ################################################################################

    def keyPressEvent(self, event):
        """Handle keys being pressed"""
        if event.key() == QtCore.Qt.Key_Space:
            self.app.request_update.emit()
            event.accept()

    def closeEvent(self, event):
        """Called when the window is closed
        @type  event: QEvent
        @param event: The close event"""
        del event
        # Only save settings on exit if toggled
        if self.saveWindowSettingsCheck.isChecked():
            self.__saveSettings()
        self.__windowClosed()

    def __restoreSettings(self):
        """Restores the windows settings"""
        self.__plugins.restoreState()

        self.setWindowTitle(self.settings.value("%s/Title" % self.name,
                                                self.app_name))
        self.restoreState(self.settings.value("%s/State" % self.name,
                                              QtCore.QByteArray()))
        self.resize(self.settings.value("%s/Size" % self.name,
                                        QtCore.QSize(1280, 1024)))
        self.move(self.settings.value("%s/Position" % self.name,
                                      QtCore.QPoint(0, 0)))

        self.saveWindowSettingsCheck.setChecked(self.settings.value("SaveOnExit", "true") == "true")

    def __saveSettingsToggle(self, checked):
        """Toggles saving window settings on exit"""

        # Make sure that it has the same state in all windows
        for window in self.windows:
            window.saveWindowSettingsCheck.setChecked(checked)

    def __saveSettings(self):
        """Saves the windows settings"""
        logger.info('Saving: %s', self.settings.fileName())

        self.__plugins.saveState()

        # For populating the default state: print self.saveState().toBase64()

        # Only update open/close state if at least one window is still open
        if self.windows:
            # Save the fact that this window is open or not
            for windowName in self.windows_names:
                for window in self.windows:
                    if window.name == windowName:
                        self.settings.setValue("%s/Open" % windowName, True)
                        break
                else:
                    self.settings.setValue("%s/Open" % windowName, False)

        # Save other window state
        self.settings.setValue("Version", self.app_version)

        self.settings.setValue("%s/Title" % self.name,
                               self.windowTitle())
        self.settings.setValue("%s/State" % self.name,
                               self.saveState())
        self.settings.setValue("%s/Size" % self.name,
                               self.size())
        self.settings.setValue("%s/Position" % self.name,
                               self.pos())

        self.settings.setValue("SaveOnExit", self.saveWindowSettingsCheck.isChecked())

    def __revertLayout(self):
        """Revert back to default window layout"""
        result = QtWidgets.QMessageBox.question(
                    self,
                    "Restart required ",
                    MainWindow.USER_CONFIRM_RESTART,
                    QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)

        if result == QtWidgets.QMessageBox.Yes:
            self.settings.setValue("RevertLayout", True)
            self.__windowCloseApplication()

    def __enableJobInteraction(self):
        """ Enable/Disable user job interaction """
        result = QtWidgets.QMessageBox.question(
                    self,
                    "Job Interaction Settings ",
                    MainWindow.USER_CONFIRM_RESTART,
                    QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)

        if result == QtWidgets.QMessageBox.Yes:
            # currently not enabled, user wants to enable
            if self.__isEnabled is False:
                self.settings.setValue("EnableJobInteraction", 1)
                self.__windowCloseApplication()
            else:
                self.settings.setValue("EnableJobInteraction", 0)
                self.__windowCloseApplication()
