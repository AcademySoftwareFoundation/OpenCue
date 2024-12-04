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


"""Base class for any cue nodes to work with NodeGraphQtPy"""


from builtins import str
from NodeGraphQtPy import BaseNode
from cuegui.nodegraph.widgets.nodeWidgets import NodeProgressBar


class CueBaseNode(BaseNode):
    """Base class for any cue nodes to work with NodeGraphQtPy"""

    __identifier__ = "aswf.opencue"

    NODE_NAME = "Base"

    def __init__(self, rpcObject=None):
        super(CueBaseNode, self).__init__()
        self.add_input(name="parent", multi_input=True, display_name=False)
        self.add_output(name="children", multi_output=True, display_name=False)

        self.rpcObject = rpcObject

    def setRpcObject(self, rpcObject):
        """Set the nodes rpc object
        @param rpc object to set on node
        @type opencue.wrappers.layer.Layer
        """
        self.rpcObject = rpcObject

    def addProgressBar(
        self,
        name="",
        label="",
        value=0,
        max_value=100,
        display_format="%p%",
        tab=None
    ):
        """Add progress bar property to node
        @param name: name of the custom property
        @type name: str
        @param label: label to be displayed
        @type label: str
        @param value: value to set progress bar to
        @type value: int
        @param max_value: max_value value progress bar can go up to
        @type max_value: int
        @param display_format: string format to display value on progress bar with
        @type display_format: str
        @param tab:name of the widget tab to display in.
        @type tab: str
        """
        self.create_property(
            name, str(value), tab=tab
        )
        widget = NodeProgressBar(
            self.view,name,
            label,
            value,
            max_value=max_value,
            display_format=display_format
        )
        widget.value_changed.connect(self.set_property)
        self.view.add_widget(widget)
