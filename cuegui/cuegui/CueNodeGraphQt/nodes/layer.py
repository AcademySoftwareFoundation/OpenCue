from __future__ import division
import os
from PySide2 import QtGui
import NodeGraphQt.qgraphics.node_base
from cuegui.CueNodeGraphQt.nodes.base import CueBaseNode
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
        if layerRpcObject.data.services:
            app = layerRpcObject.data.services[0]
            images_path = cuegui.images.__path__[0]
            icon_path = os.path.join(images_path, 'apps', app + '.png')
            if os.path.exists(icon_path):
                self.set_icon(icon_path)

        self.add_progress_bar(
            'succeededFrames',
            '',
            layerRpcObject.succeededFrames(),
            max=layerRpcObject.totalFrames(),
            format='%v / %m'
        )

        self.update_node_color(layerRpcObject)
        font = self.view.text_item.font()
        font.setPointSize(16)
        self.view.text_item.setFont(font)

    def update_node_color(self, layerRpcObject):
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

    def set_rpcObject(self, rpcObject):
        super(CueLayerNode, self).set_rpcObject(rpcObject)
        self.set_property('succeededFrames', rpcObject.succeededFrames())
        self.update_node_color(rpcObject)
