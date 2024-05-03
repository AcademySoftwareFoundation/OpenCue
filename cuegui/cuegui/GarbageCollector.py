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
can crash."""


import gc

from qtpy import QtCore


class GarbageCollector(QtCore.QObject):
    """Custom garbage collector class.

    Disables automatic garbage collection and instead collect manually every INTERVAL milliseconds.

    This is done to ensure that garbage collection only happens in the GUI thread, as otherwise Qt
    can crash."""

    INTERVAL = 5000

    def __init__(self, parent, debug=False):
        QtCore.QObject.__init__(self, parent)
        self.debug = debug

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.check)  # pylint: disable=no-member

        self.threshold = gc.get_threshold()
        gc.disable()
        self.timer.start(self.INTERVAL)

    def check(self):
        """Runs the garbage collector.

        This method is run every INTERNAL seconds."""
        gc.collect()
        if self.debug:
            for obj in gc.garbage:
                print(obj, repr(obj), type(obj))
