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
Main entry point for the application.
"""
import os

import Constants
import Logger
import Style
from MainWindow import MainWindow
from Manifest import QtCore, QtGui, QtWidgets
from ThreadPool import ThreadPool

logger = Logger.getLogger(__file__)


class CueGuiApplication(QtWidgets.QApplication):

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

    def __init__(self, *args, **kwargs):
        super(CueGuiApplication, self).__init__(*args, **kwargs)


def cuetopia(argv):
    startup("Cuetopia", Constants.VERSION, argv)


def cuecommander(argv):
    startup("CueCommander", Constants.VERSION, argv)


def startup(app_name, app_version, argv):
    app = CueGuiApplication(argv)

    # Start splash screen
    from SplashWindow import SplashWindow
    splash = SplashWindow(app, app_name, app_version, Constants.RESOURCE_PATH)
    # Display a splash message with: splash.msg("Message")

    # Allow ctrl-c to kill the application
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    # Load window icon
    app.setWindowIcon(QtGui.QIcon('%s/images/windowIcon.png' % Constants.RESOURCE_PATH))

    app.setApplicationName(app_name)
    app.lastWindowClosed.connect(app.quit)

    QtGui.qApp.threadpool = ThreadPool(3)

    config_path = "/.%s/config" % app_name.lower()
    settings = QtCore.QSettings(QtCore.QSettings.IniFormat, QtCore.QSettings.UserScope, config_path)
    QtGui.qApp.settings = settings

    Style.init()

    # If the config file does not exist, copy over the default
    local = "%s%s.ini" % (os.getenv("HOME"), config_path)
    if not os.path.exists(local):
        default = os.path.join(Constants.DEFAULT_INI_PATH, "%s.ini" % app_name.lower())
        print "Not found: %s\nCopying:   %s" % (local, default)
        try:
            os.mkdir(os.path.dirname(local))
        except Exception, e:
            logger.debug(e)
        try:
            import shutil
            shutil.copy2(default, local)
        except Exception, e:
            logger.debug(e)
        settings.sync()

    mainWindow = MainWindow(app_name, app_version,  None)
    mainWindow.displayStartupNotice()
    mainWindow.show()

    # Open all windows that were open when the app was last closed
    for name in mainWindow.windows_names[1:]:
        if settings.value("%s/Open" % name, False):
            mainWindow.windowMenuOpenWindow(name)

    # End splash screen
    splash.hide()

    app.exec_()
