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


"""Base class representing a cue node"""


from builtins import str
from NodeGraphQt import BaseNode
from cuegui.nodegraph.widgets.nodeWidgets import NodeProgressBar



class CueBaseNode(BaseNode):

    __identifier__ = 'aswf.opencue'

    NODE_NAME = 'Base'

    def __init__(self, rpcObject=None):
        super(CueBaseNode, self).__init__()
        self.add_input(name='parent', multi_input=True, display_name=False)
        self.add_output(name='children', multi_output=True, display_name=False)

        self.rpcObject = rpcObject

    def setRpcObject(self, rpcObject):
        self.rpcObject = rpcObject

    def addProgressBar(self, name='', label='', value=0, max=100, format='%p%', tab=None):
        self.create_property(
            name, str(value), tab=tab
        )
        widget = NodeProgressBar(self.view, name, label, value, max=max, format=format)
        widget.value_changed.connect(lambda k, v: self.set_property(k, v))
        self.view.add_widget(widget)
