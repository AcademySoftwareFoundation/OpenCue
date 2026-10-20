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


"""Custom garbage collector class.

Disables automatic garbage collection and instead collect manually every INTERVAL milliseconds.

This is done to ensure that garbage collection only happens in the GUI thread, as otherwise Qt
can crash. Only the youngest generations are collected every INTERVAL milliseconds; the full heap
is collected every FULL_COLLECTION_TICKS ticks."""


import gc

from qtpy import QtCore


class GarbageCollector(QtCore.QObject):
    """Custom garbage collector class.

    Disables automatic garbage collection and instead collect manually every INTERVAL milliseconds.

    This is done to ensure that garbage collection only happens in the GUI thread, as otherwise Qt
    can crash. Only the youngest generations are collected every INTERVAL milliseconds; the full
    heap is collected every FULL_COLLECTION_TICKS ticks."""

    INTERVAL = 5000
    # Collecting the full heap takes tens of milliseconds once large trees are loaded, so it only
    # runs every 5 minutes.
    FULL_COLLECTION_TICKS = 60

    def __init__(self, parent, debug=False):
        QtCore.QObject.__init__(self, parent)
        self.debug = debug
        self.ticks = 0

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.check)  # pylint: disable=no-member

        self.threshold = gc.get_threshold()
        gc.disable()
        self.timer.start(self.INTERVAL)

    def check(self):
        """Runs the garbage collector.

        This method is run every INTERVAL milliseconds. It collects the
        generations 0 and 1, and every FULL_COLLECTION_TICKS times, all of
        them."""
        self.ticks += 1
        if self.ticks >= self.FULL_COLLECTION_TICKS:
            self.ticks = 0
            gc.collect()
        else:
            gc.collect(1)
        if self.debug:
            for obj in gc.garbage:
                print(obj, repr(obj), type(obj))
