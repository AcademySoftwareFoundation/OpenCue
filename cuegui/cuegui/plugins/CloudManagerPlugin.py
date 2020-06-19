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


from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import cuegui.AbstractDockWidget
import cuegui.CloudManagerWidget


PLUGIN_NAME = "CloudManager"
PLUGIN_CATEGORY = "Cuecommander"
PLUGIN_DESCRIPTION = "An interface to manage cloud groups and hosts"
PLUGIN_REQUIRES = "CueCommander"
PLUGIN_PROVIDES = "CloudManagerDockWidget"


class CloudManagerDockWidget(cuegui.AbstractDockWidget.AbstractDockWidget):
    """This builds what is displayed on the dock widget"""

    def __init__(self, parent):
        super(CloudManagerDockWidget, self).__init__(parent, PLUGIN_NAME)

        self.__cloudManagerWidget = cuegui.CloudManagerWidget.CloudManagerWidget(self)

        self.layout().addWidget(self.__cloudManagerWidget)

        # self.pluginRegisterSettings([("columnVisibility",
        #                               self.__cloudManagerWidget.getColumnVisibility,
        #                               self.__cloudManagerWidget.setColumnVisibility)])
