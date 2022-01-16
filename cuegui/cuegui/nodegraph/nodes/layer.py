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


"""Implementation of a Cue Layer node that works with NodeGraphQt"""


from __future__ import division
import os
from PySide2 import QtGui
import NodeGraphQt.qgraphics.node_base
from cuegui.nodegraph.nodes.base import CueBaseNode
from cuegui.Constants import RGB_FRAME_STATE
import cuegui.images
import opencue


class CueLayerNode(CueBaseNode):

    __identifier__ = 'aswf.opencue'

    NODE_NAME = 'Layer'

    def __init__(self, layerRpcObject=None):
        super(CueLayerNode, self).__init__(rpcObject=layerRpcObject)

        self.set_name(layerRpcObject.name())

        NodeGraphQt.qgraphics.node_base.NODE_ICON_SIZE = 30
        services = layerRpcObject.services()
        if services:
            app = services[0].name()
            imagesPath = cuegui.images.__path__[0]
            iconPath = os.path.join(imagesPath, 'apps', app + '.png')
            if os.path.exists(iconPath):
                self.set_icon(iconPath)

        self.addProgressBar(
            'succeededFrames',
            '',
            layerRpcObject.succeededFrames(),
            max=layerRpcObject.totalFrames(),
            format='%v / %m'
        )

        self.updateNodeColour(layerRpcObject)
        font = self.view.text_item.font()
        font.setPointSize(16)
        self.view.text_item.setFont(font)

    def updateNodeColour(self, layerRpcObject):
        # default colour
        r, g, b = self.color()
        color = QtGui.QColor(r, g, b)

        # state specific colours
        if layerRpcObject.totalFrames() == layerRpcObject.succeededFrames():
            color = RGB_FRAME_STATE[opencue.api.job_pb2.SUCCEEDED]
        if layerRpcObject.waitingFrames() > 0:
            color = RGB_FRAME_STATE[opencue.api.job_pb2.WAITING]
        if layerRpcObject.dependFrames() > 0:
            color = RGB_FRAME_STATE[opencue.api.job_pb2.DEPEND]
        if layerRpcObject.runningFrames() > 0:
            color = RGB_FRAME_STATE[opencue.api.job_pb2.RUNNING]
        if layerRpcObject.deadFrames() > 0:
            color = RGB_FRAME_STATE[opencue.api.job_pb2.DEAD]

        self.set_color(
            color.red() // 2,
            color.green() // 2,
            color.blue() // 2
        )

    def setRpcObject(self, rpcObject):
        super(CueLayerNode, self).setRpcObject(rpcObject)
        self.set_property('succeededFrames', rpcObject.succeededFrames())
        self.updateNodeColour(rpcObject)
