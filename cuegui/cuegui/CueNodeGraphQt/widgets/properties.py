from Qt import QtWidgets, QtCore


class PropLayerItemWidget(QtWidgets.QWidget):
    value_changed = QtCore.Signal(str, object)

    def __init__(self, parent=None):
        super(PropLayerItemWidget, self).__init__(parent)

    def get_value(self):
        return ''

    def set_value(self, value):
        if value and value != self.get_value():
            pass
