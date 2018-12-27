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


import cuegui

PLUGIN_NAME = "Shows"
PLUGIN_CATEGORY = "Cuecommander"
PLUGIN_DESCRIPTION = "An administrator interface to shows"
PLUGIN_REQUIRES = "CueCommander3"
PLUGIN_PROVIDES = "ShowsDockWidget"

class ShowsDockWidget(cuegui.AbstractDockWidget):
    """This builds what is displayed on the dock widget"""
    def __init__(self, parent):
        cuegui.AbstractDockWidget.__init__(self, parent, PLUGIN_NAME)

        self.__showsWidget = cuegui.ShowsWidget(self)

        self.layout().addWidget(self.__showsWidget)

        self.pluginRegisterSettings([("columnVisibility",
                                      self.__showsWidget.getColumnVisibility,
                                      self.__showsWidget.setColumnVisibility)])
