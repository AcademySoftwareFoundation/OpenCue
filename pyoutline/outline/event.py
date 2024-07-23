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


"""
The outline event handler controls firing events to listeners.
"""


from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

from builtins import str
from builtins import object
import logging

from .exception import FailImmediately


logger = logging.getLogger("outline.event")

EVENT_TYPES = ("AFTER_INIT",
               "AFTER_PARENTED",
               "SETUP",
               "BEFORE_EXECUTE",
               "AFTER_EXECUTE",
               "AFTER_LAUNCH",
               "BEFORE_LAUNCH")

AFTER_INIT = EVENT_TYPES[0]
AFTER_PARENTED = EVENT_TYPES[1]
SETUP = EVENT_TYPES[2]
BEFORE_EXECUTE = EVENT_TYPES[3]
AFTER_EXECUTE = EVENT_TYPES[4]
AFTER_LAUNCH = EVENT_TYPES[5]
BEFORE_LAUNCH = EVENT_TYPES[6]


class EventHandler(object):
    """
    EventHandler keeps track of who is listening for which events.
    """
    def __init__(self, component):
        # pylint: disable=unused-private-member
        self.__component = component
        self.__listeners = {}

    def add_event_listener(self, event_type, callback):
        """
        Adds an event listener for the given type and
        callback function.
        """
        logger.debug("adding event listener %s", event_type)
        if event_type not in self.__listeners:
            self.__listeners[event_type] = []
        self.__listeners[event_type].append(callback)

    # pylint: disable=broad-except
    def emit(self, event):
        """Fires an event, calling any registered listeners."""
        logger.debug("fire event %s", event)
        for callback in self.__listeners.get(event.type, []):
            try:
                callback(event)
            except FailImmediately as fi:
                logger.debug("FailImmediately exception thrown, %s, %s", event.type, fi)
                raise fi
            except Exception as e:
                logger.debug("failed to execute event %s, %s", event.type, e)

    def get_event_listeners(self, event_type):
        """
        Return all the callback functions registered with
        a particular event type.
        """
        try:
            return self.__listeners[event_type]
        except KeyError:
            return []


class LaunchEvent(object):
    """
    A job launch event type.
    """
    def __init__(self, event_type, cuerun, **args):
        self.type = event_type
        self.cuerun = cuerun
        self.__dict__.update(args)

    def __str__(self):
        return str(self.__dict__)


class LayerEvent(object):
    """
    A LayerEvent occurs within a layer.
    """
    def __init__(self, event_type, layer, **args):
        self.type = event_type
        self.layer = layer
        self.__dict__.update(args)

    def __str__(self):
        return str(self.__dict__)
