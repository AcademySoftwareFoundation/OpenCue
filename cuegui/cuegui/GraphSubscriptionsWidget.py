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


from Manifest import QtCore, QtGui, QtWidgets, opencue


class GraphSubscriptionsWidget(QtWidgets.QWidget):
    def __init__(self, parent):
        QtWidgets.QWidget.__init__(self, parent)

        self.__color = QtGui.QColor(55,200,55)
        self.__brush = QtGui.QBrush()
        self.__brush.setColor(self.__color)
        self.__brush.setStyle(QtCore.Qt.SolidPattern)

        self.__show = opencue.api.findShow("clo")
        self.__history = [0]*100
        self.__line = 575
        self.__max = max(self.__line * 1.2, 80)

        self.__timer = QtCore.QTimer(self)
        self.__timer.timeout.connect(self.addNumber)

        self.__timer.start(10000)

    def addNumber(self):
        for sub in self.__show.getSubscriptions():
            if sub.name() == "clo.General":
                val = sub.runningCores()/100
                self.__history.append(val)
                self.__max = max(self.__max, val + 80)

        if len(self.__history) > 100:
            self.__history.pop(0)

        self.update()

    def paintEvent(self, event):
        QtWidgets.QWidget.paintEvent(self, event)

        #Skip this if too small, if splitter is all the way over

        painter = QtGui.QPainter(self)
        try:
            rect = self.contentsRect().adjusted(5, 5, -5, -5)
            painter.save()

            painter.fillRect(rect,
                             QtGui.qApp.palette().color(QtGui.QPalette.Base))




            if len(self.__history) > 1:
                stepWidth = rect.width() / float(len(self.__history) - 1)
                ratioHeight = (rect.height() - 2) / float(self.__max)

                # Box outline
                painter.setPen(QtCore.Qt.black)
                painter.drawRect(rect)

                painter.setPen(self.__color)
                points = QtGui.QPolygon(len(self.__history) + 2)

                # Bottom left
                #points.setPoint(0, rect.bottomLeft())
                points.setPoint(0, rect.left() + 1, rect.bottom())

                # All the data points
                num = 1
                for i in range(len(self.__history)):
                    points.setPoint(num,
                                    max(rect.x() + 1, rect.x() - 1 + stepWidth * i),
                                    rect.bottom() - ratioHeight * self.__history[i])
                    num += 1

                # Bottom right
                points.setPoint(num, rect.bottomRight())

                # Draw filled in
                painter.setBrush(self.__brush)
                painter.drawPolygon(points)

                # Draw subscription size line
                painter.setPen(QtCore.Qt.red)
                height = rect.bottom() - ratioHeight * self.__line
                painter.drawLine(rect.left() + 1,
                                 height,
                                 rect.right() - 1,
                                 height)

        finally:
            painter.restore()
            painter.end()
            del painter
