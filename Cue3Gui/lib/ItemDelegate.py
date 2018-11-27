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


from math import ceil

import Constants
import Utils
from Manifest import Cue3, QtCore, QtGui

RGB_FRAME_STATE = {Cue3.api.job_pb2.SUCCEEDED: QtGui.QColor(55, 200, 55),
                   Cue3.api.job_pb2.RUNNING: QtGui.QColor(200, 200, 55),
                   Cue3.api.job_pb2.WAITING: QtGui.QColor(135, 207, 235),
                   Cue3.api.job_pb2.DEPEND: QtGui.QColor(160, 32, 240),
                   Cue3.api.job_pb2.DEAD: QtGui.QColor(255, 0, 0),
                   Cue3.api.job_pb2.EATEN: QtGui.QColor(150, 0, 0)}

# This controls display order
FRAME_STATES = (Cue3.api.job_pb2.SUCCEEDED,
                Cue3.api.job_pb2.RUNNING,
                Cue3.api.job_pb2.WAITING,
                Cue3.api.job_pb2.DEPEND,
                Cue3.api.job_pb2.DEAD,
                Cue3.api.job_pb2.EATEN)

NO_PEN = QtGui.QPen(QtCore.Qt.NoPen)


class AbstractDelegate(QtGui.QItemDelegate):
    """Handles drawing of items for the TreeWidget. Provides special handling
    for selected jobs in order to still display background color."""
    __colorInvalid = QtGui.QColor()
    __brushSelected = QtGui.QBrush(QtCore.Qt.Dense4Pattern)
    __colorUsed = QtGui.QColor(255, 0, 0)
    __colorFree = QtGui.QColor(0, 255, 0)

    def __init__(self, parent, jobProgressBarColumn = None, *args):
        QtGui.QItemDelegate.__init__(self, parent, *args)

    def paint(self, painter, option, index):
        if option.state & QtGui.QStyle.State_Selected:
            # If selected cell
            self._paintSelected(painter, option, index)
        else:
            # Everything else
            QtGui.QItemDelegate.paint(self, painter, option, index)

    def _paintDifferenceBar(self, painter, option, index, used, total):
        if not total:
            return
        painter.save()
        try:
            self._drawBackground(painter, option, index)

            rect = option.rect.adjusted(2, 6, -2, -6)
            ratio = rect.width() / float(total)
            length = int(ceil(ratio * (used)))
            painter.fillRect(rect,
                             self.__colorUsed)
            painter.fillRect(rect.adjusted(length, 0, 0, 0),
                             self.__colorFree)

            if option.state & QtGui.QStyle.State_Selected:
                self._drawSelectionOverlay(painter, option)
        finally:
            painter.restore()
            del painter

    def _drawProgressBar(self, painter, rect, frameStateTotals):
        """Returns the list that defines the column.
        @type  painter: QPainter
        @param painter: The painter to draw with
        @type  rect: QRect
        @param rect: The area to draw in
        @type  frameStateTotals: dict
        @param frameStateTotals: Dictionary of frame states and their amount"""
        ratio = rect.width() / float(sum(frameStateTotals.values()))
        for frameState in FRAME_STATES:
            length = int(ceil( ratio * frameStateTotals[frameState]))
            if length > 0:
                rect.setWidth(length)
                painter.fillRect(rect, RGB_FRAME_STATE[frameState])
                rect.setX(rect.x() + length)

    def _paintSelected(self, painter, option, index):
        painter.save()
        try:
            self._drawBackground(painter, option, index)

            # Draw the selection overlay
            self._drawSelectionOverlay(painter, option)

            # Draw the icon, if any
            value = index.data(QtCore.Qt.DecorationRole)
            if not value.isNull():
                icon = QtGui.QIcon(value)
                icon.paint(painter,
                           option.rect.adjusted(3, 1, -1, -1),
                           QtCore.Qt.AlignLeft)
                option.rect.adjust(22, 0, 0, 0)

            # Draw the text
            painter.setPen(QtGui.QColor(index.data(QtCore.Qt.ForegroundRole)))
            # TODO: Disable to fix OSX styling - b/120096941
            # painter.setFont(QtGui.QFont(index.data(QtCore.Qt.FontRole)))
            painter.drawText(option.rect.adjusted(3, -1, -3, 0),
                             index.data(QtCore.Qt.TextAlignmentRole).toInt()[0] | QtCore.Qt.AlignVCenter,
                             index.data(QtCore.Qt.DisplayRole).toString())
        finally:
            painter.restore()
            del painter

    def _drawBackground(self, painter, option, index):
        # Draw the background color
        painter.setPen(NO_PEN)
        # TODO: Disable to fix OSX styling - b/120096941
        # painter.setBrush(QtGui.QBrush(index.data(QtCore.Qt.BackgroundRole)))
        painter.drawRect(option.rect)

    def _drawSelectionOverlay(self, painter, option):
        # Draw the selection
        if option.rect.width() > 0:
            QtGui.qDrawPlainRect(painter, option.rect, self.__colorInvalid, 0,
                                 self.__brushSelected)

class JobBookingBarDelegate(AbstractDelegate):
    def __init__(self, parent, *args):
        AbstractDelegate.__init__(self, parent, *args)

    def paint(self, painter, option, index):
        # Only if job
        if index.data(QtCore.Qt.UserRole).toInt()[0] == Constants.TYPE_JOB and \
           option.rect.width() > 30:
                # This itemFromIndex could cause problems
                # I need: minCores, maxCores, totalRunning, totalWaiting
                job = self.parent().itemFromIndex(index).iceObject

                rect = option.rect.adjusted(12, 6, -12, -6)

                jobMin = int(job.data.minCores * 100)
                jobMax = int(job.data.maxCores * 100)
                jobRunning = job.data.runningFrames
                jobWaiting = job.data.waitingFrames

                painter.save()
                try:
                    self._drawBackground(painter, option, index)

                    try:
                        ratio = rect.width() / float(jobRunning + jobWaiting)

                        if jobWaiting:
                            painter.fillRect(rect.adjusted(0, 2, 0, -2),
                                             RGB_FRAME_STATE[Cue3.api.job_pb2.FrameState.Waiting])

                        if jobRunning:
                            painter.fillRect(rect.adjusted(0, 0, -int(ceil(ratio * jobWaiting)), 0),
                                             RGB_FRAME_STATE[Cue3.api.job_pb2.FrameState.Running])

                        painter.setPen(QtCore.Qt.blue)
                        x = min(rect.x() + ratio * jobMin, option.rect.right() - 9)
                        painter.drawLine(x, option.rect.y(), x, option.rect.y() + option.rect.height())

                        painter.setPen(QtCore.Qt.red)
                        x = min(rect.x() + ratio * jobMax, option.rect.right() - 6)
                        painter.drawLine(x, option.rect.y(), x, option.rect.y() + option.rect.height())

                    except ZeroDivisionError:
                        pass

                    if option.state & QtGui.QStyle.State_Selected:
                        self._drawSelectionOverlay(painter, option)
                finally:
                    painter.restore()
                    del painter
        else:
            AbstractDelegate.paint(self, painter, option, index)

class JobThinProgressBarDelegate(AbstractDelegate):
    def __init__(self, parent, *args):
        AbstractDelegate.__init__(self, parent, *args)

    def paint(self, painter, option, index):
        # Only if job
        if index.data(QtCore.Qt.UserRole).toInt()[0] == Constants.TYPE_JOB:
            frameStateTotals = index.data(QtCore.Qt.UserRole + 1).toPyObject()
            painter.save()
            try:
                self._drawBackground(painter, option, index)

                self._drawProgressBar(painter,
                                      option.rect.adjusted(0, 6, 0, -6),
                                      frameStateTotals)

                if option.state & QtGui.QStyle.State_Selected:
                    self._drawSelectionOverlay(painter, option)
            finally:
                painter.restore()
                del painter
        else:
            AbstractDelegate.paint(self, painter, option, index)

class JobProgressBarDelegate(AbstractDelegate):
    def __init__(self, parent, *args):
        AbstractDelegate.__init__(self, parent, *args)

    def paint(self, painter, option, index):
        if index.data(QtCore.Qt.UserRole).toInt()[0] == Constants.TYPE_JOB:
            # This is a lot of data calls to build this one item
            frameStateTotals = index.data(QtCore.Qt.UserRole + 1).toPyObject()
            state = index.data(QtCore.Qt.UserRole + 2).toPyObject()
            paused = index.data(QtCore.Qt.UserRole + 3).toBool()

            painter.save()
            try:
                try:
                    self._drawProgressBar(painter,
                                          option.rect.adjusted(0, 2, 0, -2),
                                          frameStateTotals)

                    if state == Cue3.api.job_pb2.FINISHED:
                        painter.setPen(QtCore.Qt.black)
                        painter.drawText(option.rect, 0, QtCore.QString("Finished"))
                    elif paused:
                        painter.setPen(QtCore.Qt.blue)
                        painter.drawText(option.rect, 0, QtCore.QString("Paused"))
                except Exception, e:
                    print "Exception:", e
                    painter.setPen(QtCore.Qt.red)
                    painter.drawText(option.rect, 0, QtCore.QString("Gui Error"))
            finally:
                painter.restore()
                del painter
        else:
            AbstractDelegate.paint(self, painter, option, index)

class HostSwapBarDelegate(AbstractDelegate):
    def __init__(self, parent, *args):
        AbstractDelegate.__init__(self, parent, *args)

    def paint(self, painter, option, index):
        if index.data(QtCore.Qt.UserRole).toInt()[0] == Constants.TYPE_HOST:
            self._paintDifferenceBar(painter, option, index,
                                     *index.data(QtCore.Qt.UserRole + 1).toPyObject())
        else:
            AbstractDelegate.paint(self, painter, option, index)

class HostMemBarDelegate(AbstractDelegate):
    def __init__(self, parent, *args):
        AbstractDelegate.__init__(self, parent, *args)

    def paint(self, painter, option, index):
        if index.data(QtCore.Qt.UserRole).toInt()[0] == Constants.TYPE_HOST:
            self._paintDifferenceBar(painter, option, index,
                                     *index.data(QtCore.Qt.UserRole + 2).toPyObject())
        else:
            AbstractDelegate.paint(self, painter, option, index)

class HostGpuBarDelegate(AbstractDelegate):
    def __init__(self, parent, *args):
        AbstractDelegate.__init__(self, parent, *args)

    def paint(self, painter, option, index):
        if index.data(QtCore.Qt.UserRole).toInt()[0] == Constants.TYPE_HOST:
            self._paintDifferenceBar(painter, option, index,
                                     *index.data(QtCore.Qt.UserRole + 3).toPyObject())
        else:
            AbstractDelegate.paint(self, painter, option, index)

class HostHistoryDelegate(AbstractDelegate):
#To use this delegate, the host item must have this:
#in __init__:
#        self.coresHistory = [object.coresReserved()]
#    def update(self, object = None, parent = None):
#        if object:
#            self.coresHistory.append(object.coresReserved())
#            if len(self.coresHistory) > 40:
#                self.coresHistory.pop(0)
#        AbstractWidgetItem.update(self, object, parent)

    def __init__(self, parent, *args):
        AbstractDelegate.__init__(self, parent, *args)
        self.__color = QtGui.QColor(55,200,55)
        self.__brush = QtGui.QBrush()
        self.__brush.setColor(self.__color)
        self.__brush.setStyle(QtCore.Qt.SolidPattern)

    def paint(self, painter, option, index):
        if index.data(QtCore.Qt.UserRole).toInt()[0] == Constants.TYPE_HOST:
            hostItem = self.parent().itemFromIndex(index)
            host = hostItem.iceObject

            painter.save()
            try:
                self._drawBackground(painter, option, index)

                if len(hostItem.coresHistory) > 1:
                    stepWidth = option.rect.width() / float(len(hostItem.coresHistory) - 1)
                    ratioHeight = (option.rect.height() - 2) / float(host.data.cores)

                    painter.setPen(QtCore.Qt.black)
                    painter.drawRect(option.rect)

                    painter.setPen(self.__color)

                    points = QtGui.QPolygon(len(hostItem.coresHistory) + 2)
                    points.setPoint(0, option.rect.bottomLeft())
                    num = 1
                    for i in range(len(hostItem.coresHistory)):
                        points.setPoint(num, option.rect.x() + stepWidth * i, option.rect.bottom() - ratioHeight * hostItem.coresHistory[i])
                        num += 1
                    points.setPoint(num, option.rect.bottomRight())

                    painter.setBrush(self.__brush)

                    painter.drawPolygon(points)

                if option.state & QtGui.QStyle.State_Selected:
                    self._drawSelectionOverlay(painter, option)
            finally:
                painter.restore()
                del painter
        else:
            AbstractDelegate.paint(self, painter, option, index)

class ItemDelegate(AbstractDelegate):
    def __init__(self, parent, *args):
        AbstractDelegate.__init__(self, parent, *args)

    def paint(self, painter, option, index):
        AbstractDelegate.paint(self, painter, option, index)
