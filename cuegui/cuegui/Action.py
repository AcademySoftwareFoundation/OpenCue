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
utility functions for creating QActions
"""


from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

from PySide2 import QtGui
from PySide2 import QtWidgets

from cuegui import Constants


Actions = {}
Groups = {}

ICON_PATH = "%s/images" % Constants.RESOURCE_PATH


def create(parent, text, tip, callback=None, icon=None):
    """create(QtGui.QWidget, string text, string tip, callable callback=None, string icon=None)
        creates a QtGui.QAction and optionally connects it to a slot
    """
    a = QtWidgets.QAction(parent)
    a.setText(text)
    if tip:
        a.setToolTip(tip)
    if icon:
        a.setIcon(QtGui.QIcon(":%s.png" % (icon)))
    if callback:
        connectActionSlot(a,callback)
    return a


def createAction(parent, id, text, tip, callback=None, icon=None):
    """create(QtWidgets.QWidget, string text, string tip, callable callback=None, string icon=None)
        creates a QtGui.QAction and optionally connects it to a slot
    """
    if id in Actions:
        raise Exception("Action %s has already been created" % (id))

    a = QtWidgets.QAction(parent)
    a.setText(text)
    if tip:
        a.setToolTip(tip)
    if icon:
        a.setIcon(QtGui.QIcon(":/images/%s.png" % icon))
    if callback:
        connectActionSlot(a,callback)
    Actions[id] = a
    return a


def getAction(id):
    return Actions[id]


def createActionGroup(parent, id, actions):
    g = QtWidgets.QActionGroup(parent)
    for action in actions:
        g.addAction(action)
    Groups[id] = g


def getActionGroup(id):
    return Groups[id]


def applyActionGroup(id, menu):
    for act in getActionGroup(id).actions():
        menu.addAction(act)


def connectActionSlot(action, callable):
    """connectActionSlot
        connects an action's triggered() signal to a callable object
    """
    action.triggered.connect(callable)


class Refresh(QtWidgets.QAction):
    """Refresh

        refresh something
    """

    def __init__(self,callback=None, parent=None):
        QtWidgets.QAction.__init__(self,parent)
        self.setText("Refresh")
        self.setIcon(QtGui.QIcon(":/images/stock-refresh.png"))
        if callback:
            self.triggered.connect(callback)
