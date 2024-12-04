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


"""Widget for displaying a preview of a frame in an image viewer."""


from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

import os
import subprocess
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as Et

from qtpy import QtCore
from qtpy import QtWidgets

import cuegui.Constants
import cuegui.Logger
import cuegui.Utils


logger = cuegui.Logger.getLogger(__file__)


class PreviewProcessorDialog(QtWidgets.QDialog):
    """Widget for displaying a preview of a frame in an image viewer."""

    def __init__(self, job, frame, aovs=False, parent=None):
        """
        :type  job: opencue.wrappers.job.Job
        :param job: job containing the frame
        :type  frame: opencue.wrappers.frame.Frame
        :param frame: frame to display
        :type  aovs: bool
        :param aovs: whether to display AOVs or just the main image
        :type  parent: qtpy.QtWidgets.QWidget
        :param parent: the parent widget
        """
        QtWidgets.QDialog.__init__(self, parent)
        self.app = cuegui.app()

        self.__job = job
        self.__frame = frame
        self.__aovs = aovs

        self.__previewThread = None
        # pylint: disable=unused-private-member
        self.__previewFile = None

        layout = QtWidgets.QVBoxLayout(self)

        self.__msg = QtWidgets.QLabel("Waiting for preview images...", self)
        self.__progbar = QtWidgets.QProgressBar(self)

        self.closeEvent = self.__close

        layout.addWidget(self.__msg)
        layout.addWidget(self.__progbar)

    def process(self):
        """Opens the image viewer."""
        items = []
        http_host = self.__frame.resource().split("/")[0]
        http_port = self.__findHttpPort()

        aovs = ""
        if self.__aovs:
            aovs = "/aovs"

        url = "http://%s:%d%s" % (http_host, http_port, aovs)
        with urllib.request.urlopen(url) as response:
            playlist = response.read()

        for element in Et.fromstring(playlist).findall("page/edit/element"):
            items.append(str(element.text))

        if not items:
            return

        # pylint: disable=unused-private-member
        self.__previewFile = self.__writePlaylist(playlist)
        self.__previewThread = PreviewProcessorWatchThread(items, self)
        self.app.threads.append(self.__previewThread)
        self.__previewThread.start()
        self.__progbar.setRange(0, len(items))

        self.__previewThread.existCountChanged.connect(self.updateProgressDialog)
        self.__previewThread.timeout.connect(self.processTimedOut)

    def updateProgressDialog(self, current, max_progress):
        """Updates the progress dialog."""
        if max_progress != current:
            self.__progbar.setValue(current)
        else:
            self.close()
            self.__previewThread.stop()
            self.__launchViewer()

    def __launchViewer(self):
        """Launch a viewer for this preview frame"""
        if not cuegui.Constants.OUTPUT_VIEWER_DIRECT_CMD_CALL:
            print("No viewer configured. "
                  "Please ensure output_viewer.direct_cmd_call is configured properly")
        print("Launching preview: ", self.__previewFile)
        cmd = cuegui.Constants.OUTPUT_VIEWER_DIRECT_CMD_CALL.format(
            paths=self.__previewFile).split()
        subprocess.call(cmd, shell=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def processTimedOut(self):
        """Event handler when the process has timed out."""
        self.close()
        QtWidgets.QMessageBox.critical(
            self,
            "Preview Timeout",
            "Unable to preview images, timed out while waiting for images to be copied.")

    @staticmethod
    def __writePlaylist(data):
        """Write preview data to a temporary file"""
        (fh, name) = tempfile.mkstemp(suffix=".itv", prefix="playlist")
        os.close(fh)
        with open(name, "w", encoding='utf-8') as fp:
            try:
                fp.write(data)
            finally:
                fp.close()
        return name

    def __close(self, event):
        """Close preview thread"""
        del event
        self.__previewThread.terminate = True

    def __findHttpPort(self):
        """Figure out what port is being used by the tool to write previews"""
        log = cuegui.Utils.getFrameLogFile(self.__job, self.__frame)
        with open(log, "r", encoding='utf-8') as fp:
            try:
                counter = 0
                for line in fp:
                    counter += 1
                    if counter >= 5000:
                        break
                    if "Preview Server" in line[:30]:
                        return int(line.split(":")[-1].strip())
            finally:
                fp.close()

        raise Exception("This frame doesn't support previews. No Preview Server found.")


# pylint: disable=no-member
class PreviewProcessorWatchThread(QtCore.QThread):
    """
    Waits for preview files to appear and emits the progress every second.  This
    thread times out after 60 seconds, which should only occur if there are
    serious filer problems.
    """
    existCountChanged = QtCore.Signal(int, int)
    timeout = QtCore.Signal()

    def __init__(self, items, parent=None):
        QtCore.QThread.__init__(self, parent)
        self.__items = items
        self.__timeout = 60 + (30 * len(items))
        self.terminate = False

    def run(self):
        """
        Just check to see how many files exist and
        emit that back to our parent.
        """
        start_time = time.time()
        while not self.terminate:
            count = len([path for path in self.__items if os.path.exists(path)])
            self.existCountChanged.emit(count, len(self.__items))
            if count == len(self.__items):
                break
            time.sleep(1)
            if time.time() > self.__timeout + start_time:
                self.timeout.emit()
                logger.warning('Timed out waiting for preview server.')
                break

    def stop(self):
        """Stop the preview capture thread"""
        self.terminate = True
