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

import getpass
import signal

from qtpy import QtGui
from qtpy import QtCore

import cuegui
import cuegui.Layout
import cuegui.Constants
import cuegui.Logger
import cuegui.MainWindow
import cuegui.SplashWindow
import cuegui.Style
import cuegui.ThreadPool
import cuegui.Utils
import cuegui.GarbageCollector


logger = cuegui.Logger.getLogger(__file__)


def cuetopia(argv):
    """Starts the Cuetopia window."""
    startup("Cuetopia", cuegui.Constants.VERSION, argv)


def cuecommander(argv):
    """Starts the CueCommander window."""
    startup("CueCommander", cuegui.Constants.VERSION, argv)


def startup(app_name, app_version, argv):
    """Starts an application window."""

    app = cuegui.create_app(argv)

    # Start splash screen
    splash = cuegui.SplashWindow.SplashWindow(
        app, app_name, app_version, cuegui.Constants.RESOURCE_PATH)

    # Allow ctrl-c to kill the application
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    # Load window icon
    app.setWindowIcon(QtGui.QIcon('%s/windowIcon.png' % cuegui.Constants.RESOURCE_PATH))

    app.setApplicationName(app_name)
    app.lastWindowClosed.connect(app.quit)  # pylint: disable=no-member

    app.threadpool = cuegui.ThreadPool.ThreadPool(3, parent=app)

    settings = cuegui.Layout.startup(app_name)
    app.settings = settings

    __setup_sentry()

    cuegui.Style.init()

    mainWindow = cuegui.MainWindow.MainWindow(app_name, app_version,  None)
    mainWindow.displayStartupNotice()
    mainWindow.show()

    # Allow ctrl-c to kill the application
    signal.signal(signal.SIGINT, mainWindow.handleExit)
    signal.signal(signal.SIGTERM, mainWindow.handleExit)

    # Custom qt message handler to ignore known warnings
    QtCore.qInstallMessageHandler(warning_handler)


    # Open all windows that were open when the app was last closed
    for name in mainWindow.windows_names[1:]:
        if settings.value("%s/Open" % name, "false").lower() == 'true':
            mainWindow.windowMenuOpenWindow(name)

    # End splash screen
    splash.hide()

    # TODO(#609) Refactor the CueGUI classes to make this garbage collector
    #   replacement unnecessary.
    gc = cuegui.GarbageCollector.GarbageCollector(parent=app, debug=False)  # pylint: disable=unused-variable
    app.aboutToQuit.connect(closingTime)  # pylint: disable=no-member
    app.exec_()


def __setup_sentry():
    """Setup Sentry if cuegui.Constants.SENTRY_DSN is defined."""
    dsn = cuegui.Constants.SENTRY_DSN

    if not dsn:
        logger.info("Sentry is disabled (no SENTRY_DSN configured).")
        return

    try:
        # Avoid importing sentry at top level to keep it optional
        # pylint: disable=import-outside-toplevel
        import sentry_sdk
        # pylint: enable=import-outside-toplevel
        sentry_sdk.init(dsn)
        sentry_sdk.set_user({'username': getpass.getuser()})
        logger.info("Sentry initialized successfully.")
    except ImportError:
        logger.info("Sentry DSN is set but sentry_sdk is not installed.")
    except Exception as e:
        logger.warning("Unexpected error initializing Sentry: %s", e)


def warning_handler(msg_type, msg_log_context, msg_string):
    """
    Handler qt warnings. Ignore known warning messages that happens when
    multi-threaded/multiple updates happen in a short span
    """
    if ('QTextCursor::setPosition:' in msg_string or
        'SelectionRequest too old' in msg_string):
        return

    logger.warning('%s: %s, Message: %s',
                   str(msg_type),
                   str(msg_log_context),
                   str(msg_string))


def closingTime():
    """Window close callback."""
    logger.info("Closing all threads...")
    threads = cuegui.app().threads
    for thread in threads:
        cuegui.Utils.shutdownThread(thread)
