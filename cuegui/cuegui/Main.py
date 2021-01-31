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


"""Main entry point for the application."""


from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

import os
import shutil
import signal

from PySide2 import QtCore
from PySide2 import QtGui
from PySide2 import QtWidgets

import cuegui.Constants
import cuegui.Logger
import cuegui.MainWindow
import cuegui.SplashWindow
import cuegui.Style
import cuegui.ThreadPool
import cuegui.Utils
import cuegui.GarbageCollector


logger = cuegui.Logger.getLogger(__file__)


class CueGuiApplication(QtWidgets.QApplication):
    """The CueGUI application."""

    # Global signals
    display_log_file_content = QtCore.Signal(object)
    double_click = QtCore.Signal(object)
    facility_changed = QtCore.Signal()
    single_click = QtCore.Signal(object)
    unmonitor = QtCore.Signal(object)
    view_hosts = QtCore.Signal(object)
    view_object = QtCore.Signal(object)
    view_procs = QtCore.Signal(object)
    request_update = QtCore.Signal()
    status = QtCore.Signal()
    quit = QtCore.Signal()


def cuetopia(argv):
    """Starts the Cuetopia window."""
    startup("Cuetopia", cuegui.Constants.VERSION, argv)


def cuecommander(argv):
    """Starts the CueCommander window."""
    startup("CueCommander", cuegui.Constants.VERSION, argv)


def startup(app_name, app_version, argv):
    """Starts an application window."""

    app = CueGuiApplication(argv)

    # Start splash screen
    splash = cuegui.SplashWindow.SplashWindow(
        app, app_name, app_version, cuegui.Constants.RESOURCE_PATH)

    # Allow ctrl-c to kill the application
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    # Load window icon
    app.setWindowIcon(QtGui.QIcon('%s/windowIcon.png' % cuegui.Constants.RESOURCE_PATH))

    app.setApplicationName(app_name)
    app.lastWindowClosed.connect(app.quit)

    QtGui.qApp.threadpool = cuegui.ThreadPool.ThreadPool(3, parent=app)
    QtGui.qApp.threads = []

    config_path = "/.%s/config" % app_name.lower()
    settings = QtCore.QSettings(QtCore.QSettings.IniFormat, QtCore.QSettings.UserScope, config_path)
    local = settings.fileName()
    # If the user has chose to revert the layout. delete the file and copy the default back.
    if settings.value('RevertLayout'):
        os.remove(local)

    QtGui.qApp.settings = settings

    cuegui.Style.init()

    # If the config file does not exist, copy over the default
    # pylint: disable=broad-except
    if not os.path.exists(local):
        default = os.path.join(cuegui.Constants.DEFAULT_INI_PATH, "%s.ini" % app_name.lower())
        logger.warning('Not found: %s\nCopying:   %s', local, default)
        try:
            os.mkdir(os.path.dirname(local))
        except Exception as e:
            logger.debug(e)
        try:
            shutil.copy2(default, local)
        except Exception as e:
            logger.debug(e)
        settings.sync()
    # pylint: enable=broad-except

    mainWindow = cuegui.MainWindow.MainWindow(app_name, app_version,  None)
    mainWindow.displayStartupNotice()
    mainWindow.show()

    # Open all windows that were open when the app was last closed
    for name in mainWindow.windows_names[1:]:
        if settings.value("%s/Open" % name, False):
            mainWindow.windowMenuOpenWindow(name)

    # End splash screen
    splash.hide()

    # TODO(#609) Refactor the CueGUI classes to make this garbage collector
    #   replacement unnecessary.
    # pylint: disable=unused-variable
    gc = cuegui.GarbageCollector.GarbageCollector(parent=app, debug=False)
    # pylint: enable=unused-variable
    app.aboutToQuit.connect(closingTime)
    app.exec_()


def closingTime():
    """Window close callback."""
    logger.info("Closing all threads...")
    # pylint: disable=no-member
    threads = QtGui.qApp.threads
    # pylint: enable=no-member
    for thread in threads:
        cuegui.Utils.shutdownThread(thread)
