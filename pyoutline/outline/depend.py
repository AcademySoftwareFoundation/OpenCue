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


"""Class for storing dependency data."""


from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

from builtins import str
from builtins import object


__all__ = ["Depend",
           "DependType",
           "parse_require_str"]


class DependType(object):
    """
    A class to represent a dependency between layers.

    There are three types of dependencies:
       - FrameByFrame : Where each frame of one layer depends on
                        the corresponding frame of another layer.
       - LayerOnLayer : Where all frames of one layer depend on all
                        frames of another layer.
       - PreviousFrame : Where each frame in one layer depend on
                         the previous frame of another layer.
    """
    FrameByFrame = "FRAME_BY_FRAME"
    LayerOnLayer = "LAYER_ON_LAYER"
    PreviousFrame = "PREVIOUS_FRAME"
    LayerOnSimFrame = "LAYER_ON_SIM_FRAME"
    LayerOnAny = "LAYER_ON_ANY"

    # Short depend types used in require strings.
    all = LayerOnLayer
    any = LayerOnAny
    sim = LayerOnSimFrame
    prev = PreviousFrame


def parse_require_str(require):
    """
    Parse a require string and returns its components.

    A require string is short hand for defining dependencies which contains the
    layer_name:depend_type.
    """
    parts = str(require).split(":")
    if len(parts) == 1:
        return (parts[0], DependType.FrameByFrame)
    return (parts[0], getattr(DependType, parts[1]))


class Depend(object):
    """A dependency"""

    def __init__(self, depend_er, depend_on,
                 depend_type=DependType.FrameByFrame,
                 propigate=False, any_frame=False):

        object.__init__(self)
        self.__depend_er = depend_er
        self.__depend_on = depend_on
        self.__type = depend_type
        self.__propigate = propigate
        self.__any_frame = any_frame

    def get_dependant_layer(self):
        """
        Return the dependant layer.

        :rtype: L{Layer}
        :return: The layer that is depending.
        """
        return self.__depend_er

    def get_depend_on_layer(self):
        """
        Return the layer to depend on.

        :rtype: L{Layer}
        :return: The layer that is being depended on.
        """
        return self.__depend_on

    def get_type(self):
        """
        The type of depend.

        :rtype: str
        :return: The type of dependency.
        """
        return self.__type

    def is_propagated(self):
        """
        A propagated dependency is propagated to to others layers
        automatically.  For example when a L{Layer} A depends on L{Layer} B through
        a propagated dependency, then setting up a dependency from L{Layer} C to
        L{Layer} A would automatically create a depend from L{Layer} C to L{Layer} B.

        Depends that are automatically setup between L{LayerPreProcess} and
        a L{Layer} are propagated dependencies.

        :rtype: boolean
        :return: True if he depend is propagated, false if it is not.

        """
        return self.__propigate

    def is_any_frame(self):
        """
        If any-frame is true only a single frame in the entire
        layer has to complete for the whole dependency to be satisfied.

        :rtype: boolean
        :return: True if the depend is an any frame depend.
        """
        return self.__any_frame
