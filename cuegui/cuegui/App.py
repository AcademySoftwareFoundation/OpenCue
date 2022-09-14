
from PySide6 import QtCore
from PySide6 import QtWidgets


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


def get_app():
    """Gets the current application instance."""
    return __QAPPLICATION_SINGLETON
