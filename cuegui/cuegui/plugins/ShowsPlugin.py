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


"""Plugin for listing shows and performing administrative tasks."""


from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

from qtpy import QtWidgets

import cuegui.AbstractDockWidget
import cuegui.CreateShowDialog
import cuegui.ShowsWidget


PLUGIN_NAME = "Shows"
PLUGIN_CATEGORY = "Cuecommander"
PLUGIN_DESCRIPTION = "An administrator interface to shows"
PLUGIN_REQUIRES = "CueCommander"
PLUGIN_PROVIDES = "ShowsDockWidget"


class ShowsDockWidget(cuegui.AbstractDockWidget.AbstractDockWidget):
    """Plugin for listing shows and performing administrative tasks."""

    def __init__(self, parent):
        super(ShowsDockWidget, self).__init__(parent, PLUGIN_NAME)

        self.__showsWidget = cuegui.ShowsWidget.ShowsWidget(self)
        self.__createShowButton = QtWidgets.QPushButton("Create Show")
        self.__createShowButton.setFixedWidth(150)
        self.__createShowButton.clicked.connect(self.onCreateShowClicked)  # pylint: disable=no-member

        self.layout().addWidget(self.__createShowButton)
        self.layout().addWidget(self.__showsWidget)

        self.pluginRegisterSettings([("columnVisibility",
                                      self.__showsWidget.getColumnVisibility,
                                      self.__showsWidget.setColumnVisibility),
                                      ("columnOrder",
                                      self.__showsWidget.getColumnOrder,
                                      self.__showsWidget.setColumnOrder)])

    def onCreateShowClicked(self):
        """Show the dialog for creating new shows"""
        d = cuegui.CreateShowDialog.CreateShowDialog(self)
        d.exec_()
