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


"""Implementation of a Cue Layer node that works with NodeGraphQtPy"""


from __future__ import division
import os
from qtpy import QtGui
import opencue
import NodeGraphQtPy.qgraphics.node_base
import cuegui.images
from cuegui.Constants import RGB_FRAME_STATE
from cuegui.nodegraph.nodes.base import CueBaseNode


class CueLayerNode(CueBaseNode):
    """Implementation of a Cue Layer node that works with NodeGraphQtPy"""

    __identifier__ = "aswf.opencue"

    NODE_NAME = "Layer"

    def __init__(self, layerRpcObject=None):
        super(CueLayerNode, self).__init__(rpcObject=layerRpcObject)

        self.set_name(layerRpcObject.name())

        NodeGraphQtPy.qgraphics.node_base.NODE_ICON_SIZE = 30
        services = layerRpcObject.services()
        if services:
            app = services[0].name()
            imagesPath = cuegui.images.__path__[0]
            iconPath = os.path.join(imagesPath, "apps", app + ".png")
            if os.path.exists(iconPath):
                self.set_icon(iconPath)

        self.addProgressBar(
            name="succeededFrames",
            label="",
            value=layerRpcObject.succeededFrames(),
            max_value=layerRpcObject.totalFrames(),
            display_format="%v / %m"
        )

        font = self.view.text_item.font()
        font.setPointSize(16)
        self.view.text_item.setFont(font)
        # Lock the node text so it can't be edited
        self.view.text_item.set_locked(True)

        self.setRpcObject(layerRpcObject)

    def updateNodeColour(self):
        """Update the colour of the node to reflect the status of the layer"""
        # default colour
        r, g, b = self.color()
        color = QtGui.QColor(r, g, b)

        # state specific colours
        if self.rpcObject.totalFrames() == self.rpcObject.succeededFrames():
            color = RGB_FRAME_STATE[opencue.api.job_pb2.SUCCEEDED]
        if self.rpcObject.waitingFrames() > 0:
            color = RGB_FRAME_STATE[opencue.api.job_pb2.WAITING]
        if self.rpcObject.dependFrames() > 0:
            color = RGB_FRAME_STATE[opencue.api.job_pb2.DEPEND]
        if self.rpcObject.runningFrames() > 0:
            color = RGB_FRAME_STATE[opencue.api.job_pb2.RUNNING]
        if self.rpcObject.deadFrames() > 0:
            color = RGB_FRAME_STATE[opencue.api.job_pb2.DEAD]

        self.set_color(
            color.red() // 2,
            color.green() // 2,
            color.blue() // 2
        )

    def setRpcObject(self, rpcObject):
        """Set the nodes layer rpc object
        @param rpc object to set on node
        @type opencue.wrappers.layer.Layer
        """
        super(CueLayerNode, self).setRpcObject(rpcObject)
        self.set_property("succeededFrames", rpcObject.succeededFrames())
        self.updateNodeColour()
