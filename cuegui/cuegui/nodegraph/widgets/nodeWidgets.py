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


"""Module defining custom widgets that appear on nodes in the nodegraph.

The classes defined here inherit from NodeGraphQt base classes, therefore any
snake_case methods defined here are overriding the base class and must remain
snake_case to work properly.
"""


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
        self.set_custom_widget(self._progressbar)
        self.text = str(value)

    @property
    def type_(self):
        return 'ProgressBarNodeWidget'

    def get_value(self):
        return self._progressbar.value()

    def set_value(self, value=0):
        if int(float(value)) != self.value:
            self._progressbar.setValue(int(float(value)))
            self._value_changed()
