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


"""Plugin for viewing loki logs."""

import string
import time
import datetime

from qtpy import QtCore
from qtpy import QtWidgets

from opencue.wrappers import job, frame

import cuegui.Constants
import cuegui.AbstractDockWidget

PLUGIN_NAME = 'LokiView'
PLUGIN_CATEGORY = 'Other'
PLUGIN_DESCRIPTION = 'Displays Frame Log from Loki'
PLUGIN_PROVIDES = 'LokiViewPlugin'
PRINTABLE = set(string.printable)

try:
    # pylint: disable=import-outside-toplevel
    from loki_urllib3_client import LokiClient
    LOKI_CLIENT_ENABLED = True
except ImportError:
    LOKI_CLIENT_ENABLED = False

class LokiViewWidget(QtWidgets.QWidget):
    """
    Displays the log file for the selected frame
    """
    client = None
    def __init__(self, parent=None):
        super().__init__(parent)
        self.app = cuegui.app()
        self.verticalLayout = QtWidgets.QVBoxLayout(self)
        if LOKI_CLIENT_ENABLED is False:
            errorLabel = QtWidgets.QLabel(self)
            errorLabel.setText('Loki client is not installed')
            self.verticalLayout.addWidget(errorLabel)
            return
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.frameNameLabel = QtWidgets.QLabel(self)
        self.horizontalLayout.addWidget(self.frameNameLabel)
        self.frameLogCombo = QtWidgets.QComboBox(self)
        self.frameLogCombo.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)
        self.horizontalLayout.addWidget(self.frameLogCombo)
        self.wordWrapCheck = QtWidgets.QCheckBox(self)
        self.wordWrapCheck.setText("Word Wrap")
        self.horizontalLayout.addWidget(self.wordWrapCheck)
        self.refreshButton = QtWidgets.QPushButton(self)
        self.refreshButton.setText("Refresh")
        self.horizontalLayout.addWidget(self.refreshButton)
        self.horizontalLayout.setStretch(0, 1)
        self.verticalLayout.addLayout(self.horizontalLayout)
        self.frameText = QtWidgets.QTextEdit(self)
        self.frameText.setStyleSheet("pre {display: inline;}")
        self.frameText.setLineWrapMode(QtWidgets.QTextEdit.NoWrap)
        self.frameText.setReadOnly(True)
        self.verticalLayout.addWidget(self.frameText)
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.caseCheck = QtWidgets.QCheckBox(self)
        self.caseCheck.setText("Aa")
        self.horizontalLayout_2.addWidget(self.caseCheck)
        self.searchLine = QtWidgets.QLineEdit(self)
        self.searchLine.setPlaceholderText("Search log..")
        self.searchLine.setText("")
        self.searchLine.setClearButtonEnabled(True)
        self.horizontalLayout_2.addWidget(self.searchLine)
        self.findButton = QtWidgets.QPushButton(self)
        self.findButton.setText("Find")
        self.horizontalLayout_2.addWidget(self.findButton)
        self.verticalLayout.addLayout(self.horizontalLayout_2)

        self.frameLogCombo.currentIndexChanged.connect(self._selectLog)
        self.app.select_frame.connect(self._display_frame_log)

    def _display_frame_log(self, jobObj: job.Job, frameObj: frame.Frame):
        jobName = jobObj.name()
        frameName = frameObj.name()
        frameId = frameObj.id()
        self.frameLogCombo.clear()
        if jobObj.lokiURL():
            self.frameNameLabel.setText(f"{jobName}.{frameName}")
            self.client = LokiClient(jobObj.lokiURL())
            maxTries = 5
            tries = 0
            while tries < maxTries:
                if self.client.ready() is True:
                    break
                tries += 1
                time.sleep(0.5 * tries)
            success, result = self.client.label_values(
                label="session_start_time",
                start=datetime.datetime.fromtimestamp(jobObj.startTime()),
                params={'query': f'{{frame_id="{frameId}"}}'}
            )
            if success is True:
                labelValues = result.get('data', [])
                for unix_timestamp in sorted(labelValues, reverse=True):
                    query = f'{{session_start_time="{unix_timestamp}", frame_id="{frameId}"}}'
                    data = [unix_timestamp, query]
                    self.frameLogCombo.addItem(
                        _unix_to_datetime(int(float(unix_timestamp))), userData=data
                    )
                self.frameLogCombo.adjustSize()
        else:
            pass

    # pylint: disable=unused-argument
    def _selectLog(self, index):
        self.frameText.clear()
        if self.frameLogCombo.currentData():
            timestamp, query =  self.frameLogCombo.currentData()
            start = datetime.datetime.fromtimestamp(float(timestamp))
            end = datetime.datetime.now()
            success, result = self.client.query_range(query=query,
                                                      direction=LokiClient.Direction.forward,
                                                      limit=1000, start=start, end=end)
            if success is True:
                for res in result.get('data', {}).get('result', []):
                    for timestamp, line in res.get('values'):
                        self.frameText.append(f"<pre style='margin: 0px;'>{line}</pre>")
            else:
                print(success, result)


def _unix_to_datetime(unix_timestamp):
    """Simple function to convert from timestamp to human readable string"""
    return datetime.datetime.fromtimestamp(int(unix_timestamp)).strftime('%Y-%m-%d %H:%M:%S')


class LokiViewPlugin(cuegui.AbstractDockWidget.AbstractDockWidget):
    """
    Plugin for displaying the log file content for the selected frame with
    the ability to perself regex-based search.
    """

    def __init__(self, parent=None):
        """
        Create a LogViewPlugin instance

        @param parent: The parent widget
        @type parent: QtWidgets.QWidget or None
        """
        cuegui.AbstractDockWidget.AbstractDockWidget.__init__(
            self, parent, PLUGIN_NAME, QtCore.Qt.BottomDockWidgetArea)
        self.logview_widget = LokiViewWidget(self)
        self.layout().addWidget(self.logview_widget)
