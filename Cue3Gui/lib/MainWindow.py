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


"""
All windows are an instance of this MainWindow.
"""
from Manifest import os, QtCore, QtGui, Cue3, CueConfig

import sys

import Action
import Plugins
import Utils
import Constants

class MainWindow(QtGui.QMainWindow):
    """The main window of the application. Multiple windows may exist."""
    windows = []
    windows_names = []
    windows_titles = {}
    windows_actions = {}

    def __init__(self, app_name, app_version, window_name, parent = None):
        QtGui.QMainWindow.__init__(self, parent)

        # Setup variables
        self.qApp = QtGui.qApp
        self.settings = QtGui.qApp.settings
        self.windows_names = [app_name] + ["%s_%s" % (app_name, num) for num in xrange(2,5)]
        self.app_name = app_name
        self.app_version = app_version
        if window_name:
            self.name = window_name
        else:
            self.name = self.windows_names[0]

        # Provides a location for widgets to the right of the menu
        menuLayout = QtGui.QHBoxLayout()
        menuLayout.addStretch()
        self.menuBar().setLayout(menuLayout)

        # Configure window
        self.setMinimumSize(600, 400)
        self.setAnimated(False)
        self.setDockNestingEnabled(True)

        # Register this window
        self.__windowOpened()

        # Create menus
        self.__createMenus()

        # Setup plugins
        self.__plugins = Plugins.Plugins(self, self.name)
        self.__plugins.setupPluginMenu(self.PluginMenu)

        # Restore saved settings
        self.__restoreSettings()

        QtCore.QObject.connect(QtGui.qApp,
                               QtCore.SIGNAL('status(PyQt_PyObject)'),
                               self.showStatusBarMessage)

        self.showStatusBarMessage("Ready")

    def displayStartupNotice(self):
        import time
        now = int(time.time())
        lastView = self.settings.value("LastNotice", QtCore.QVariant(0)).toInt()[0]
        if lastView < Constants.STARTUP_NOTICE_DATE:
            QtGui.QMessageBox.information(self, "Notice", Constants.STARTUP_NOTICE_MSG, QtGui.QMessageBox.Ok)
        self.settings.setValue("LastNotice", QtCore.QVariant(now))

    def showStatusBarMessage(self, message, delay = 5000):
        self.statusBar().showMessage(str(message), delay)

    def displayAbout(self):
        msg = self.app_name + "\n\nA Cue3 tool\n\n"
        msg += "Qt:\n%s\n\n" % QtCore.qVersion()
        msg += "Python:\n%s\n\n" % sys.version
        QtGui.QMessageBox.about(self, "About", msg)

    def openSuggestionPage(self):
        Utils.openURL(Constants.URL_SUGGESTION)

    def openBugPage(self):
        Utils.openURL(Constants.URL_BUG)

    def openUserGuide(self):
        Utils.openURL(Constants.URL_USERGUIDE)

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
        menu.setFont(Constants.STANDARD_FONT)
        QtCore.QObject.connect(menu, QtCore.SIGNAL("triggered(QAction*)"), self.__facilityMenuHandle)

        self.facility_default = CueConfig.get("cuebot.facility_default")
        self.facility_dict = CueConfig.get("cuebot.facility")

        for facility in self.facility_dict:
            self.__actions_facility[facility] = QtGui.QAction(facility, menu)
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
            for facility in self.__actions_facility.itervalues():
                if facility.isChecked():
                    checked = True
            if not checked:
                self.__actions_facility[self.facility_default].setChecked(True)
        # Uncheck all other facilities if one is checked
        else:
            for facility in self.__actions_facility:
                if facility != action.text():
                    self.__actions_facility[facility].setChecked(False)

        for facility in self.__actions_facility.itervalues():
            if facility.isChecked():
                Cue3.Cuebot.setFacility(str(facility.text()))
                QtGui.qApp.emit(QtCore.SIGNAL("facility_changed()"))
                return

################################################################################

    def __createMenus(self):
        """Creates the menus at the top of the window"""
        self.menuBar().setFont(Constants.STANDARD_FONT)

        # Menu bar
        self.fileMenu = self.menuBar().addMenu("&File")
        self.facilityMenu = self.__facilityMenuSetup(self.menuBar().addMenu("&Cuebot"))
        self.PluginMenu = self.menuBar().addMenu("&Views/Plugins")
        self.windowMenu = self.menuBar().addMenu("&Window")
        self.helpMenu = self.menuBar().addMenu("&Help")

        # Menu Bar: File -> Close Window
        close = QtGui.QAction(QtGui.QIcon('icons/exit.png'), '&Close Window', self)
        close.setStatusTip('Close Window')
        QtCore.QObject.connect(close, QtCore.SIGNAL('triggered()'), self.__windowCloseWindow)
        self.fileMenu.addAction(close)

        # Menu Bar: File -> Exit Application
        exit = QtGui.QAction(QtGui.QIcon('icons/exit.png'), 'E&xit Application', self)
        exit.setShortcut('Ctrl+Q')
        exit.setStatusTip('Exit application')
        QtCore.QObject.connect(exit, QtCore.SIGNAL('triggered()'), self.__windowCloseApplication)
        self.fileMenu.addAction(exit)

        self.__windowMenuSetup(self.windowMenu)

        self.windowMenu.addSeparator()

        self.__toggleFullscreenSetup(self.windowMenu)

        # Menu Bar: Help -> Online User Guide.
        action = QtGui.QAction('Online User Guide', self)
        QtCore.QObject.connect(action, QtCore.SIGNAL('triggered()'), self.openUserGuide)
        self.helpMenu.addAction(action)

        # Menu Bar: Help -> Make a Suggestion
        action = QtGui.QAction('Make a Suggestion', self)
        QtCore.QObject.connect(action, QtCore.SIGNAL('triggered()'), self.openSuggestionPage)
        self.helpMenu.addAction(action)

        # Menu Bar: Help -> Report a Bug
        action = QtGui.QAction('Report a Bug', self)
        QtCore.QObject.connect(action, QtCore.SIGNAL('triggered()'), self.openBugPage)
        self.helpMenu.addAction(action)

        self.helpMenu.addSeparator()

        # Menu Bar: Help -> About
        about = QtGui.QAction(QtGui.QIcon('icons/about.png'), 'About', self)
        about.setShortcut('F1')
        about.setStatusTip('About')
        QtCore.QObject.connect(about, QtCore.SIGNAL('triggered()'), self.displayAbout)
        self.helpMenu.addAction(about)

################################################################################
# Handles adding windows
################################################################################

    def __windowMenuSetup(self, menu):
        """Creates the menu items for dealing with multiple main windows"""
        self.windowMenu = menu

        # Menu Bar: Window -> Change Window Title
        changeTitle = QtGui.QAction("Change Window Title", self)
        QtCore.QObject.connect(changeTitle, QtCore.SIGNAL('triggered()'), self.__windowMenuHandleChangeTitle)
        menu.addAction(changeTitle)

        # Menu Bar: Window -> Save Window Settings
        saveWindowSettings = QtGui.QAction("Save Window Settings", self)
        QtCore.QObject.connect(saveWindowSettings, QtCore.SIGNAL('triggered()'), self.__saveSettings)
        menu.addAction(saveWindowSettings)

        menu.addSeparator()

        # Load list of window titles
        if not self.windows_titles:
            for name in self.windows_names:
                self.windows_titles[name] =  str(self.settings.value("%s/Title" % name, QtCore.QVariant(name)).toString())

        # Create menu items for Window -> Open/Raise/Add Window "?"
        for name in self.windows_names:
            if not self.windows_actions.has_key(name):
                self.windows_actions[name] = QtGui.QAction("", self)

            menu.addAction(self.windows_actions[name])

        QtCore.QObject.connect(self.windowMenu, QtCore.SIGNAL("triggered(QAction*)"), self.__windowMenuHandle)

        self.__windowMenuUpdate()

    def __windowMenuUpdate(self):
        """Updates the QAction for each main window"""
        number = 1
        for name in self.windows_names:
            title = self.settings.value("%s/Title" % name, QtCore.QVariant("")).toString()
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
            for name in self.windows_titles:
                if self.windows_titles[name] == window_title:
                    self.windowMenuOpenWindow(name)

        elif action_title.endswith("Add new window") and len(action_title) == 18:
            number = int(action_title[1:].split(")")[0]) - 1
            self.windowMenuOpenWindow(self.windows_names[number])

        elif action_title.startswith("Raise Window: "):
            for window in self.windows:
                if str(window.windowTitle()) == action_title.replace("Raise Window: ",""):
                    window.raise_()
                    return

    def __windowMenuHandleChangeTitle(self):
        """Changes the title of the current window"""
        # Change the title of the current window
        (value, choice) = QtGui.QInputDialog.getText(self, "Rename window","Please provide a title for the window", QtGui.QLineEdit.Normal, str(self.windowTitle()))
        if choice:
            # Don't allow the same name twice
            for window in self.windows:
                if window.name == str(value) or str(window.windowTitle()) == str(value):
                    return
            self.setWindowTitle(str(value))
            self.windows_titles[self.name] = str(value)

        # Save the new title to settings
        self.settings.setValue("%s/Title" % self.name,
                               QtCore.QVariant(self.windowTitle()))

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
        QtCore.QObject.connect(self.qApp, QtCore.SIGNAL('quit()'), self, QtCore.SLOT('close()'))
        self.windows.append(self)
        self.qApp.closingApp = False

    def __windowClosed(self):
        """Called from closeEvent on window close"""

        # Disconnect to avoid multiple attempts to close a window
        QtCore.QObject.disconnect(self.qApp, QtCore.SIGNAL('quit()'), self, QtCore.SLOT('close()'))

        # Save the fact that this window is open or not when the app closed
        self.settings.setValue("%s/Open" % self.name,
                               QtCore.QVariant(self.qApp.closingApp))

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
        self.qApp.closingApp = True
        self.qApp.emit(QtCore.SIGNAL('quit()'))

################################################################################

    def __toggleFullscreenSetup(self, menu):
        # Menu Bar: Window -> Toggle Full-Screen
        fullscreen = QtGui.QAction(QtGui.QIcon('icons/fullscreen.png'), 'Toggle Full-Screen', self)
        fullscreen.setShortcut('Ctrl+F')
        fullscreen.setStatusTip('Toggle Full-Screen')
        QtCore.QObject.connect(fullscreen, QtCore.SIGNAL('triggered()'), self.__toggleFullscreen)
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
        if event.key() == QtCore.Qt.Key_Space:
            QtGui.qApp.emit(QtCore.SIGNAL("request_update()"))
            event.accept()

    def closeEvent(self, event):
        """Called when the window is closed
        @type  event: QEvent
        @param event: The close event"""
        self.__saveSettings()
        self.__windowClosed()

    def __restoreSettings(self):
        """Restores the windows settings"""
        self.__plugins.restoreState()

        self.setWindowTitle(self.settings.value("%s/Title" % self.name,
                                                QtCore.QVariant(self.app_name)).toString())
        self.restoreState(self.settings.value("%s/State" % self.name,
                                              QtCore.QVariant(QtCore.QByteArray())).toByteArray())
        self.resize(self.settings.value("%s/Size" % self.name,
                                        QtCore.QVariant(QtCore.QSize(1280,1024))).toSize())
        self.move(self.settings.value("%s/Position" % self.name,
                                      QtCore.QVariant(QtCore.QPoint(0,0))).toPoint())

    def __saveSettings(self):
        """Saves the windows settings"""
        print "Saving: %s" % self.settings.fileName()

        self.__plugins.saveState()

        # For populating the default state: print self.saveState().toBase64()

        self.settings.setValue("Version", QtCore.QVariant(self.app_version))

        self.settings.setValue("%s/Title" % self.name,
                               QtCore.QVariant(self.windowTitle()))
        self.settings.setValue("%s/State" % self.name,
                               QtCore.QVariant(self.saveState()))
        self.settings.setValue("%s/Size" % self.name,
                               QtCore.QVariant(self.size()))
        self.settings.setValue("%s/Position" % self.name,
                               QtCore.QVariant(self.pos()))
