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

from PySide2 import QtCore
from PySide2 import QtWidgets

import cuegui.Exception

__QAPPLICATION_SINGLETON = None


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


def create_app(argv):
    """
    Create an instance of the CueGUI application.

    :param argv: user-provided commandline arguments
    :type argv: list
    :return: the application instance
    :rtype: CueGuiApplication
    """
    global __QAPPLICATION_SINGLETON
    if __QAPPLICATION_SINGLETON is None:
        __QAPPLICATION_SINGLETON = CueGuiApplication(argv)
    return __QAPPLICATION_SINGLETON


def app():
    """Returns the current application instance.

    :return: the current application instance
    :rtype: CueGuiApplication
    :raises: opencue.exception.ApplicationNotRunningException: the application has not been initialized yet
    """
    if __QAPPLICATION_SINGLETON is None:
        raise cuegui.Exception.ApplicationNotRunningException()
    return __QAPPLICATION_SINGLETON
