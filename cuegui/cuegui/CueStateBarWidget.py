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


"""Widget that graphically displays the state of all jobs displayed."""


from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import threading
import time
import weakref

from qtpy import QtCore
from qtpy import QtGui
from qtpy import QtWidgets

import cuegui.Logger


logger = cuegui.Logger.getLogger(__file__)


class CueStateBarWidget(QtWidgets.QWidget):
    """Widget that graphically displays the state of all jobs displayed."""

    __colorInvalid = QtGui.QColor()
    __brushPattern = QtGui.QBrush(QtCore.Qt.Dense4Pattern)

    def __init__(self, sourceTree, parent=None):
        """CueStateBar init
        @type  sourceTree: QTreeWidget
        @param sourceTree: The tree to get the jobs from
        @type  parent: QWidget
        @param parent: The parent widget"""
        QtWidgets.QWidget.__init__(self, parent)
        self.app = cuegui.app()

        self.__background = None

        self.setContentsMargins(8, 1, 1, 1)
        self.setFixedWidth(22)

        self.__sourceTree = weakref.proxy(sourceTree)
        self.__colors = []
        self.__baseColor = self.app.palette().color(QtGui.QPalette.Base)
        self.__colorsLock = QtCore.QReadWriteLock() # pylint: disable=no-member
        self.__timer = QtCore.QTimer(self) # pylint: disable=no-member
        self.__lastUpdate = 0

        self.__timer.timeout.connect(self.updateColors)  # pylint: disable=no-member
        self.__sourceTree.verticalScrollBar().valueChanged.connect(self.update)
        self.__sourceTree.verticalScrollBar().rangeChanged.connect(self.__updateColors)

        self.__timer.start(10000)

    def mousePressEvent(self, mouseEvent):
        """Sets the position on the scroll bar based on the click position
        @type  mouseEvent: QEvent
        @param mouseEvent: The mouse click event"""
        self.__movePosition(mouseEvent.y())

    def mouseMoveEvent(self, mouseEvent):
        """Sets the position on the scroll bar based on the mouse position
        @type  mouseEvent: QEvent
        @param mouseEvent: The mouse click event"""
        self.__movePosition(mouseEvent.y())

    def __movePosition(self, yPos):
        """Sets the position on the scroll bar based on the given position
        @type  yPos: int
        @param yPos: Vertical position on the widget"""
        scrollBar = self.__sourceTree.verticalScrollBar()
        docLength = scrollBar.maximum() + scrollBar.pageStep()
        pos = yPos * docLength/float(self.height())

        scrollBar.setValue(int(pos - scrollBar.pageStep() / 2))

    def paintEvent(self, event):
        """Called when the widget is being redrawn
        @type  event: QEvent
        @param event: The draw event"""
        del event
        assert threading.current_thread().name == "MainThread"
        self.__colorsLock.lockForWrite()
        try:
            if not self.__colors:
                return
            colors = self.__colors
        finally:
            self.__colorsLock.unlock()

        painter = QtGui.QPainter(self)
        painter.save()
        try:
            rect = self.contentsRect()

            # Number of pixels per job
            ratio = float(rect.height())/len(colors)
            # How far down the slider is
            shift = self.__sourceTree.verticalScrollBar().value() * ratio
            # Length not covered by the slider
            offPage = self.__sourceTree.verticalScrollBar().maximum() * ratio

            painter.drawPixmap(self.contentsRect(),
                               self.__background,
                               self.__background.rect())

            # Draw the slider
            pen = QtGui.QPen(self.__colorInvalid)
            pen.setWidth(0)
            painter.setPen(pen)
            painter.setBrush(self.__brushPattern)
            painter.drawRect(rect.adjusted(2, shift, -2, -offPage + shift))
        finally:
            painter.restore()
            painter.end()
            del painter

    def __updateBackgroundPixmap(self, colors):
        """Updates the background image buffer based on the given colors
        @type  colors: list<QBrush>
        @param colors: List of job background colors"""
        # Could draw it the max size and allow the resize on drawPixmap
        # that way the same buffer is always used
        assert threading.current_thread().name == "MainThread"
        buffer = QtGui.QPixmap(self.contentsRect().size())
        buffer.fill(self.__baseColor)

        if colors:
            painter = QtGui.QPainter()
            painter.begin(buffer)
            try:
                rect = buffer.rect()

                # Number of jobs
                amount = len(colors)
                # Number of pixels per job
                ratio = float(rect.height())/amount

                for index, color in enumerate(colors):
                    if color:
                        painter.fillRect(rect.adjusted(0,
                                                       ratio * index,
                                                       0,
                                                       -(ratio * (amount - index - 1))),
                                         color)
            finally:
                painter.end()
                del painter

        self.__background = buffer

    def updateColors(self):
        """Calls __updateColors if it has been sufficient time since the last
        update"""
        if time.time() - self.__lastUpdate > 10:
            self.__updateColors()

    def __updateColors(self):
        """Calls __processUpdateColors in 1 second"""
        self.__lastUpdate = time.time()
        QtCore.QTimer.singleShot(1000, self.__processUpdateColors) # pylint: disable=no-member

    def __processUpdateColors(self):
        """Updates the list of colors to display
        calls __updateBackgroundPixmap to build pixmap
        calls update to redraw"""
        items = self.__sourceTree.findItems("",
                                            QtCore.Qt.MatchContains |
                                            QtCore.Qt.MatchRecursive,
                                            0)

        colors = []
        for item in items:
            color = QtGui.QBrush(item.data(0, QtCore.Qt.BackgroundRole))
            if color.color() == self.__baseColor:
                colors.append(None)
            else:
                colors.append(color)

        self.__colorsLock.lockForWrite()
        try:
            self.__colors = colors
        finally:
            self.__colorsLock.unlock()

        self.__updateBackgroundPixmap(colors)

        self.update()
