from Qt import QtWidgets, QtCore
import NodeGraphQt
from NodeGraphQt.widgets.node_widgets import NodeBaseWidget


class NodeProgressBar(NodeBaseWidget):
    """
    ProgressBar Node Widget.
    """

    def __init__(self, parent=None, name='', label='', value=0, max=100, format='%p%'):
        super(NodeProgressBar, self).__init__(parent, name, label)
        self._progressbar = QtWidgets.QProgressBar()
        self._progressbar.setAlignment(QtCore.Qt.AlignCenter)
        self._progressbar.setFormat(format)
        self._progressbar.setMaximum(max)
        self._progressbar.setValue(value)
        progress_style = '''
QProgressBar {
    background-color: rgba(40, 40, 40, 255);
    border: 1px solid grey;
    border-radius: 1px;
    margin: 0px;
}
QProgressBar::chunk {
    background-color: rgba(100, 120, 250, 150);
}
        '''
        self._progressbar.setStyleSheet(progress_style)
        self.setWidget(self._progressbar)
        self.text = str(value)

    @property
    def type_(self):
        return 'ProgressBarNodeWidget'

    @property
    def widget(self):
        return self._progressbar

    @property
    def value(self):
        return self._progressbar.value()

    @value.setter
    def value(self, value=0):
        if int(float(value)) != self.value:
            self._progressbar.setValue(int(float(value)))
            self._value_changed()
