#  Copyright (c) 2018 Sony Pictures Imageworks Inc.
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


"""
From katana
"""
from Manifest import QtCore, QtGui
import math

class FrameRangeSelectionWidget(QtGui.QWidget):
    """The Timeline Widget is a rectangular area with ticks to represent units
        of frames. A frame range may be selected.
        This widget emits the following signals:
        * startFrameChanged(int) - user clicks new time or program changes time
        * endFrameChanged(int) - user clicks new time or program changes time
        * frameRangeChanged(int,int) - program changes viewed frame range
        * selectionChanged(int,int) - user releases a drag that selects a frame range
        """

    def __init__(self, parent, *args):
        QtGui.QWidget.__init__(self, parent, *args)
        self.setMinimumWidth(100)
        self.__layout =  QtGui.QHBoxLayout(self)
        self.__layout.addStretch(100)

        self.__right_margin = 25
        self.__layout.setContentsMargins(0,0,0,0)
        toolButton = QtGui.QToolButton()
        toolButton.setArrowType(QtCore.Qt.UpArrow)
        toolButton.setFocusPolicy(QtCore.Qt.NoFocus)
        toolButton.setFixedSize(20,20)
        #toolButton.setContentsMargins(0,0,0,0)
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
        return self.__endFrame
    def setEndTime(self, t, final = True):
        if (self.__endFrame == t and self.__endFrameFinal == final): return
        self.__endFrame = int(t)
        self.__endFrameFinal = final

        #mine
        self.__selectionRange = (self.__startFrame, self.__endFrame)

        self.update()
        self.emit(QtCore.SIGNAL('endFrameChanged(int)'), int(t))

    # The current time displayed in the timeline.
    def startFrame(self):
        return self.__startFrame
    def setStartTime(self, t, final = True):
        if (self.__startFrame == t and self.__startFrameFinal == final): return
        self.__startFrame = int(t)
        self.__startFrameFinal = final

        if self.__endFrame == self.__startFrame:
            self.setEndTime(min(self.__startFrame + self.default_select_size - 1, self.__frameRange[1]), True)

        self.__selectionRange = (self.__startFrame, self.__endFrame)

        self.update()
        self.emit(QtCore.SIGNAL('startFrameChanged(int)'), int(t))

    # The viewed range of time in the timeline.
    def frameRange(self): return self.__frameRange
    def setFrameRange(self, frameRange):
        frameRange = tuple(sorted(map(int, frameRange)))

        self.__floatTime = None

        self.__frameRange = frameRange
        self.setStartTime(self.__frameRange[0], False)
        self.setEndTime(self.__frameRange[1], False)

        self.emit(QtCore.SIGNAL('frameRangeChanged(int,int)'),
                    self.__frameRange[0], self.__frameRange[1])
        self.update()

    # The selected (highlighted) range of time in the timeline.
    def selectedFrameRange(self): return self.__selectionRange
    def setSelectedFrameRange(self, selectedRange):
        if selectedRange != self.__selectionRange:
            self.__selectionRange = selectedRange

        self.emit(QtCore.SIGNAL('selectionChanged(int,int)'),
                  self.__selectionRange[0], self.__selectionRange[1])

    # QT event handlers and implementation details below this line.

    def mousePressEvent(self, mouseEvent):
        hitTime = self.__getTimeFromLocalPoint(mouseEvent.x())
        if mouseEvent.buttons() & QtCore.Qt.LeftButton:

            self.setStartTime(hitTime, False)
            self.__selectionRange = (hitTime, hitTime)

    def mouseMoveEvent(self, mouseEvent):
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
        if self.__double:
            self.__double = False
            self.setStartTime(self.__frameRange[0], True)
            self.setEndTime(self.__frameRange[1], True)
        else:
            hitTime = self.__getTimeFromLocalPoint(mouseEvent.x())
            self.setEndTime(max(hitTime, self.startFrame()), True)
            self.setStartTime(min(hitTime, self.startFrame()), True)

        self.__selectionRange = (min(self.__selectionRange[0], self.__selectionRange[1]), max(self.__selectionRange[0], self.__selectionRange[1]))
        self.setSelectedFrameRange(self.__selectionRange)

        self.update()

    def mouseDoubleClickEvent(self, mouseEvent):
        self.__double = True

    def paintEvent(self, paintEvent):
        painter = QtGui.QPainter(self)
        self.__paintBackground(painter)

        # Put the baseline at 0, 0
        painter.translate(0, self.height() / 2)
        painter.setFont(self.__labelFont)
        self.__paintSelection(painter)
        self.__paintTickmarks(painter)
        self.__paintLabels(painter)
        self.__paintFloatTime(painter)
        self.__paintStartTime(painter)
        self.__paintEndTime(painter)

    def leaveEvent(self, event):
        self.__floatTime = None
        self.update()

    def __getTickAreaExtent(self):
        return QtCore.QRect(10, -self.height()/2, self.width() - self.__right_margin - 20, self.height())

    def __getTickArea(self, time):
        tickArea = self.__getTickAreaExtent()
        tickSpacing = float(self.__getTickAreaExtent().width()) / max(1,(self.__frameRange[1] - self.__frameRange[0]))
        return QtCore.QRect(tickArea.left() + tickSpacing * (time - self.__frameRange[0]),
                        tickArea.top(), tickSpacing, tickArea.height())

    def __getTimeFromLocalPoint(self, x):
        tickSpacing = float(self.__getTickAreaExtent().width()) / max(1,(self.__frameRange[1] - self.__frameRange[0]))
        deltaX = x - self.__getTickAreaExtent().left()
        hitTime = int(deltaX / tickSpacing + 0.5) + self.__frameRange[0]
        hitTime = int(max(self.__frameRange[0], min(hitTime, self.__frameRange[1])))
        return hitTime

    def __getLabelPeriod(self):
        delta = self.__frameRange[1] - self.__frameRange[0]
        if (delta < 20):
            return 2
        if (delta < 10000):
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
        painter.fillRect(0, self.height()/2, self.width() - self.__right_margin+5, self.height()/2,  highlightBrush)

    def __paintTickmarks(self, painter):
        tickExtent = self.__getTickAreaExtent()
        tickHeight = tickExtent.height() / 8

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
        labelHeight = tickExtent.height() / 3
        labelPeriod = self.__getLabelPeriod()
        if labelPeriod == 0: return

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
        painter.setPen(self.palette().color(QtGui.QPalette.Foreground))
        for frame in frames:
            xPos = self.__getTickArea(frame).left()
            painter.drawLine(xPos, -labelHeight, xPos, 0)

        painter.setPen(QtGui.QColor(10, 10, 10))

        metric = QtGui.QFontMetrics(painter.font())
        yPos =  metric.ascent() + 1
        rightEdge = -10000
        width = metric.width(str(frames[-1]))
        farEdge = self.__getTickArea(frames[-1]).right() - width / 2

        farEdge -= 4

        for frame in frames:
            xPos = self.__getTickArea(frame).left()
            frameString = str(frame)
            width = metric.width(frameString)
            xPos = xPos - width / 2
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
        frameString = QtCore.QString(frameString)
        xPos = timeExtent.left() - metric.width(frameString) / 2
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
        frameString = QtCore.QString(frameString)
        xPos = timeExtent.left() - metric.width(frameString) / 2
        yPos =  metric.ascent() + 1
        painter.drawText(xPos, yPos, frameString)
        painter.setPen(oldPen)

    def __paintFloatTime(self, painter):
        if self.__floatTime == None: return

        timeExtent = self.__getTickArea(self.__floatTime)
        oldPen = painter.pen()
        painter.setPen(QtGui.QColor(90, 90, 90))
        painter.drawLine(timeExtent.left(), timeExtent.top(), timeExtent.left(), timeExtent.bottom())

        if self.__selectionRange:
            painter.setPen(QtGui.QColor(255,255,255))
        else:
            painter.setPen(QtGui.QColor(128, 128, 128))
        metric = QtGui.QFontMetrics(painter.font())
        frameString = QtCore.QString(str(self.__floatTime))
        xPos = timeExtent.left() - metric.width(frameString) / 2
        yPos =  timeExtent.top() + metric.ascent()
        painter.drawText(xPos, yPos, frameString)
        painter.setPen(oldPen)

    def __paintSelection(self, painter):
        if self.__selectionRange == None: return
        selection = (min(self.__selectionRange[0], self.__selectionRange[1]), max(self.__selectionRange[0], self.__selectionRange[1]))

        leftExtent = self.__getTickArea(selection[0])
        rightExtent = self.__getTickArea(selection[1] - 1)
        selectionExtent = QtCore.QRect(leftExtent.left(), leftExtent.top(), rightExtent.right() - leftExtent.left() + 2, leftExtent.height()/2)
        painter.fillRect(selectionExtent, QtGui.QBrush(QtGui.QColor(75, 75, 75)))
