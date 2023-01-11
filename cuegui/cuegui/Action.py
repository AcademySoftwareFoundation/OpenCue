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


"""Utility functions for creating QActions."""


from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

from qtpy import QtGui
from qtpy import QtWidgets

import cuegui.Constants


Actions = {}
Groups = {}

ICON_PATH = "%s/images" % cuegui.Constants.RESOURCE_PATH


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


def createAction(parent, action_id, text, tip, callback=None, icon=None):
    """Creates a QtGui.QAction and optionally connects it to a slot.

    create(QtWidgets.QWidget, string text, string tip, callable callback=None, string icon=None)"""
    if action_id in Actions:
        raise Exception("Action %s has already been created" % (action_id))

    a = QtWidgets.QAction(parent)
    a.setText(text)
    if tip:
        a.setToolTip(tip)
    if icon:
        a.setIcon(QtGui.QIcon(":/images/%s.png" % icon))
    if callback:
        connectActionSlot(a,callback)
    Actions[action_id] = a
    return a


def getAction(action_id):
    """Gets an action by ID."""
    return Actions[action_id]


def createActionGroup(parent, action_id, actions):
    """Creates an action group."""
    g = QtWidgets.QActionGroup(parent)
    for action in actions:
        g.addAction(action)
    Groups[action_id] = g


def getActionGroup(group_id):
    """Gets an action group."""
    return Groups[group_id]


def applyActionGroup(group_id, menu):
    """Add all actions in a group to the given menu."""
    for act in getActionGroup(group_id).actions():
        menu.addAction(act)


def connectActionSlot(action, actionCallable):
    """Connects an action's triggered() signal to a callable object."""
    action.triggered.connect(actionCallable)


class Refresh(QtWidgets.QAction):
    """Refreshes something."""

    def __init__(self,callback=None, parent=None):
        QtWidgets.QAction.__init__(self,parent)
        self.setText("Refresh")
        self.setIcon(QtGui.QIcon(":/images/stock-refresh.png"))
        if callback:
            self.triggered.connect(callback)  # pylint: disable=no-member
