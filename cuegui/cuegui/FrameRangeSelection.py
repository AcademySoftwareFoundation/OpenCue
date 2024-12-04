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


"""Widget for displaying and selecting within a frame range."""


from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from builtins import str
from builtins import map
from builtins import range
import math

from qtpy import QtCore
from qtpy import QtGui
from qtpy import QtWidgets


class FrameRangeSelectionWidget(QtWidgets.QWidget):
    """Widget for displaying and selecting within a frame range.

    A rectangular area with ticks to represent units of frames.

    This widget emits the following signals:
    * startFrameChanged(int) - user clicks new time or program changes time
    * endFrameChanged(int) - user clicks new time or program changes time
    * frameRangeChanged(int,int) - program changes viewed frame range
    * selectionChanged(int,int) - user releases a drag that selects a frame range
    """
    endFrameChanged = QtCore.Signal(int)
    startFrameChanged = QtCore.Signal(int)
    frameRangeChanged = QtCore.Signal(int, int)
    selectionChanged = QtCore.Signal(int, int)

    def __init__(self, parent, *args):
        QtWidgets.QWidget.__init__(self, parent, *args)
        self.setMinimumWidth(100)
        self.__layout = QtWidgets.QHBoxLayout(self)
        self.__layout.addStretch(100)

        self.__right_margin = 25
        self.__layout.setContentsMargins(0, 0, 0, 0)
        toolButton = QtWidgets.QToolButton()
        toolButton.setArrowType(QtCore.Qt.UpArrow)
        toolButton.setFocusPolicy(QtCore.Qt.NoFocus)
        toolButton.setFixedSize(20, 20)
        self.__layout.addWidget(toolButton)

        self.setLayout(self.__layout)

        self.setFixedHeight(25)

        self.__endFrame = 5000
        self.__endFrameFinal = True

        self.__startFrame = 1
        self.__startFrameFinal = True

        # The range we are displaying
        self.__frameRange = (self.__startFrame, self.__endFrame)
        # The range selected, or None if nothing is selected.
        self.__selectionRange = None

        # floatTime is the time the mouse is floating over.
        self.__floatTime = None

        # Request mouseover events from QT.
        self.setMouseTracking(True)

        # Don't erase the background for us; we redraw everything
        # with offscreen buffers.
        self.setAutoFillBackground(False)

        self.__labelFont = QtGui.QFont('Helvetica', 8)
        self.__double = False

        self.default_select_size = 1000

    def endFrame(self):
        """Returns the current end frame displayed in the timeline."""
        return self.__endFrame

    def setEndTime(self, t, final = True):
        """Sets the current end frame displayed in the timeline."""
        if self.__endFrame == t and self.__endFrameFinal == final:
            return
        self.__endFrame = int(t)
        self.__endFrameFinal = final

        self.__selectionRange = (self.__startFrame, self.__endFrame)

        self.update()
        self.endFrameChanged.emit(int(t))

    def startFrame(self):
        """Returns the current start frame displayed in the timeline."""
        return self.__startFrame

    def setStartTime(self, t, final = True):
        """Sets the current start frame displayed in the timeline."""
        if self.__startFrame == t and self.__startFrameFinal == final:
            return
        self.__startFrame = int(t)
        self.__startFrameFinal = final

        if self.__endFrame == self.__startFrame:
            self.setEndTime(
                min(self.__startFrame + self.default_select_size - 1, self.__frameRange[1]), True)

        self.__selectionRange = (self.__startFrame, self.__endFrame)

        self.update()
        self.startFrameChanged.emit(int(t))

    def frameRange(self):
        """Returns the viewed range of time in the timeline."""
        return self.__frameRange

    def setFrameRange(self, frameRange):
        """Sets the viewed frame range in the timeline."""
        frameRange = tuple(sorted(map(int, frameRange)))

        self.__floatTime = None

        self.__frameRange = frameRange
        self.setStartTime(self.__frameRange[0], False)
        self.setEndTime(self.__frameRange[1], False)

        self.frameRangeChanged.emit(self.__frameRange[0], self.__frameRange[1])
        self.update()

    def selectedFrameRange(self):
        """Returns the selected (highlighted) range of time in the timeline."""
        return self.__selectionRange

    def setSelectedFrameRange(self, selectedRange):
        """Sets the selected (highlighted) range of time in the timeline."""
        if selectedRange != self.__selectionRange:
            self.__selectionRange = selectedRange

        self.selectionChanged.emit(self.__selectionRange[0], self.__selectionRange[1])

    # QT event handlers and implementation details below this line.

    def mousePressEvent(self, mouseEvent):
        """Event triggered by a mouse click"""
        hitTime = self.__getTimeFromLocalPoint(mouseEvent.x())
        if mouseEvent.buttons() & QtCore.Qt.LeftButton:

            self.setStartTime(hitTime, False)
            self.__selectionRange = (hitTime, hitTime)

    def mouseMoveEvent(self, mouseEvent):
        """Event triggered by a mouse movement"""
        self.__floatTime = None

        hitTime = self.__getTimeFromLocalPoint(mouseEvent.x())

        if mouseEvent.buttons() & QtCore.Qt.LeftButton \
            or mouseEvent.buttons() & QtCore.Qt.RightButton:
            # Update the selection range, but don't send signals.
            if self.__selectionRange:
                self.__selectionRange = (self.__selectionRange[0], hitTime)
                self.setEndTime(hitTime, True)
            else:
                self.__selectionRange = (hitTime, hitTime)

        self.__floatTime = hitTime
        self.update()

    def mouseReleaseEvent(self, mouseEvent):
        """Event triggered when a mouse click is released"""
        if self.__double:
            self.__double = False
            self.setStartTime(self.__frameRange[0], True)
            self.setEndTime(self.__frameRange[1], True)
        else:
            hitTime = self.__getTimeFromLocalPoint(mouseEvent.x())
            self.setEndTime(max(hitTime, self.startFrame()), True)
            self.setStartTime(min(hitTime, self.startFrame()), True)

        self.__selectionRange = (
            min(self.__selectionRange[0], self.__selectionRange[1]),
            max(self.__selectionRange[0], self.__selectionRange[1]))
        self.setSelectedFrameRange(self.__selectionRange)

        self.update()

    def mouseDoubleClickEvent(self, mouseEvent):
        """Event triggered by a double click"""
        del mouseEvent
        self.__double = True

    def paintEvent(self, paintEvent):
        """Paint event"""
        del paintEvent
        painter = QtGui.QPainter(self)
        self.__paintBackground(painter)

        # Put the baseline at 0, 0
        painter.translate(0, self.height() // 2)
        painter.setFont(self.__labelFont)
        self.__paintSelection(painter)
        self.__paintTickmarks(painter)
        self.__paintLabels(painter)
        self.__paintFloatTime(painter)
        self.__paintStartTime(painter)
        self.__paintEndTime(painter)

    def leaveEvent(self, event):
        """Triggered at the end of any event"""
        del event
        self.__floatTime = None
        self.update()

    def __getTickAreaExtent(self):
        """Return a QRect with the selectable area"""
        return QtCore.QRect(
            10, -self.height() // 2, self.width() - self.__right_margin - 20, self.height())

    def __getTickArea(self, time):
        """Get a QRect with a tick area"""
        tickArea = self.__getTickAreaExtent()
        tickSpacing = (
                float(self.__getTickAreaExtent().width()) /
                max(1, (self.__frameRange[1] - self.__frameRange[0])))
        return QtCore.QRect(tickArea.left() + tickSpacing * (time - self.__frameRange[0]),
                        tickArea.top(), tickSpacing, tickArea.height())

    def __getTimeFromLocalPoint(self, x):
        """Get time from a local point"""
        tickSpacing = (
                float(self.__getTickAreaExtent().width()) /
                max(1, (self.__frameRange[1] - self.__frameRange[0])))
        deltaX = x - self.__getTickAreaExtent().left()
        hitTime = int(deltaX / tickSpacing + 0.5) + self.__frameRange[0]
        hitTime = int(max(self.__frameRange[0], min(hitTime, self.__frameRange[1])))
        return hitTime

    def __getLabelPeriod(self):
        delta = self.__frameRange[1] - self.__frameRange[0]
        if delta < 20:
            return 2
        if delta < 10000:
            base = 5
            offset = 2
        else:
            base = 10
            offset = 1
        scale = math.ceil(math.log(self.__frameRange[1] - self.__frameRange[0]) / math.log(base))
        return base ** max(1, scale - offset)

    def __paintBackground(self, painter):
        bgBrush = self.palette().window()
        painter.fillRect(0, 0, self.width() - self.__right_margin, self.height(), bgBrush)
        highlightBrush = QtGui.QBrush(QtGui.QColor(75, 75, 75))
        painter.fillRect(
            0,
            self.height() // 2,
            self.width() - self.__right_margin + 5,
            self.height() // 2,
            highlightBrush)

    def __paintTickmarks(self, painter):
        tickExtent = self.__getTickAreaExtent()
        tickHeight = tickExtent.height() // 8

        pen = QtGui.QPen(self.palette().window().color())
        painter.setPen(pen)

        # Draw the baseline
        painter.drawLine(tickExtent.left(), 0, tickExtent.right(), 0)

        tickArea = self.__getTickArea(self.__frameRange[0])
        if tickArea.width() >= 5:
            for frame in range(self.__frameRange[0], self.__frameRange[1] + 1, 1):
                xPos = self.__getTickArea(frame).left()
                painter.drawLine(xPos, -tickHeight, xPos, 0)

    def __paintLabels(self, painter):
        tickExtent = self.__getTickAreaExtent()
        labelHeight = tickExtent.height() // 3
        labelPeriod = self.__getLabelPeriod()
        if labelPeriod == 0:
            return

        firstLabel = self.__frameRange[0] + labelPeriod - 1
        firstLabel = firstLabel - (firstLabel % labelPeriod)

        frames = []
        for frame in range(int(firstLabel), int(self.__frameRange[1])+1, int(labelPeriod)):
            frames.append(frame)
        if frames[0] != self.__frameRange[0]:
            frames.insert(0, self.__frameRange[0])
        if frames[-1] != self.__frameRange[1]:
            frames.append(self.__frameRange[1])

        oldPen = painter.pen()

        # draw hatches for labelled frames
        painter.setPen(self.palette().color(QtGui.QPalette.WindowText))
        for frame in frames:
            xPos = self.__getTickArea(frame).left()
            painter.drawLine(xPos, -labelHeight, xPos, 0)

        painter.setPen(QtGui.QColor(10, 10, 10))

        metric = QtGui.QFontMetrics(painter.font())
        yPos = metric.ascent() + 1
        rightEdge = -10000
        width = metric.horizontalAdvance(str(frames[-1]))
        farEdge = self.__getTickArea(frames[-1]).right() - width // 2

        farEdge -= 4

        for frame in frames:
            xPos = self.__getTickArea(frame).left()
            frameString = str(frame)
            width = metric.horizontalAdvance(frameString)
            xPos = xPos - width // 2
            if (xPos > rightEdge and xPos + width < farEdge) or frame is frames[-1]:
                painter.drawText(xPos, yPos, frameString)
                rightEdge = xPos + width + 4
        painter.setPen(oldPen)

    def __paintStartTime(self, painter):
        startFrame = self.startFrame()
        timeExtent = self.__getTickArea(startFrame)
        oldPen = painter.pen()
        painter.setPen(QtGui.QColor(0, 255, 0))
        painter.drawLine(timeExtent.left(), timeExtent.top(), timeExtent.left(), 0)

        metric = QtGui.QFontMetrics(painter.font())
        frameString = str(int(startFrame))
        xPos = timeExtent.left() - metric.horizontalAdvance(frameString) // 2
        yPos =  metric.ascent() + 1
        painter.drawText(xPos, yPos, frameString)
        painter.setPen(oldPen)

    def __paintEndTime(self, painter):
        endFrame = self.endFrame()
        timeExtent = self.__getTickArea(endFrame)
        oldPen = painter.pen()
        painter.setPen(QtGui.QColor(255, 0, 0))
        painter.drawLine(timeExtent.left(), timeExtent.top(), timeExtent.left(), 0)

        metric = QtGui.QFontMetrics(painter.font())
        frameString = str(int(endFrame))
        xPos = timeExtent.left() - metric.horizontalAdvance(frameString) // 2
        yPos = metric.ascent() + 1
        painter.drawText(xPos, yPos, frameString)
        painter.setPen(oldPen)

    def __paintFloatTime(self, painter):
        if self.__floatTime is None:
            return

        timeExtent = self.__getTickArea(self.__floatTime)
        oldPen = painter.pen()
        painter.setPen(QtGui.QColor(90, 90, 90))
        painter.drawLine(
            timeExtent.left(), timeExtent.top(), timeExtent.left(), timeExtent.bottom())

        if self.__selectionRange:
            painter.setPen(QtGui.QColor(255,255,255))
        else:
            painter.setPen(QtGui.QColor(128, 128, 128))
        metric = QtGui.QFontMetrics(painter.font())
        frameString = str(self.__floatTime)
        xPos = timeExtent.left() - metric.horizontalAdvance(frameString) // 2
        yPos = timeExtent.top() + metric.ascent()
        painter.drawText(xPos, yPos, frameString)
        painter.setPen(oldPen)

    def __paintSelection(self, painter):
        if self.__selectionRange is None:
            return
        selection = (
            min(self.__selectionRange[0], self.__selectionRange[1]),
            max(self.__selectionRange[0], self.__selectionRange[1]))

        leftExtent = self.__getTickArea(selection[0])
        rightExtent = self.__getTickArea(selection[1] - 1)
        selectionExtent = QtCore.QRect(
            leftExtent.left(),
            leftExtent.top(),
            rightExtent.right() - leftExtent.left() + 2,
            leftExtent.height() // 2)
        painter.fillRect(selectionExtent, QtGui.QBrush(QtGui.QColor(75, 75, 75)))
