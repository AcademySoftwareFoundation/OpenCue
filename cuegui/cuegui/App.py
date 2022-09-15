
from PySide2 import QtCore
from PySide2 import QtWidgets

import opencue.exception

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
    global __QAPPLICATION_SINGLETON
    if __QAPPLICATION_SINGLETON is None:
        __QAPPLICATION_SINGLETON = CueGuiApplication(argv)
    return __QAPPLICATION_SINGLETON


def app():
    """Returns the current application instance."""
    if __QAPPLICATION_SINGLETON is None:
        raise opencue.exception.CueException('application has not been initialized, create_app() must be called first')
    return __QAPPLICATION_SINGLETON
