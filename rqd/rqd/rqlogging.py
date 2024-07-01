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


"""Logging module, handles logging to files and non-files"""

import time
import os
import tempfile
import datetime


def createLogger(filepath):
    """Wrapper to create the RQDLogger object"""
    f = RQDLogger(filepath)
    return f


class RQDLogger(tempfile.SpooledTemporaryFile):
    """Class to abstract file logging, this class tries to act as a file object"""
    filepath = None
    fd = None

    def __init__(self, filepath):
        """RQDLogger class initialization
           @type    filepath: string
           @param   filepath: The filepath to log to
        """
        super().__init__()
        self.filepath = filepath
        self.fd = open(self.filepath, "w+", 1)

    # pylint: disable=arguments-differ
    def write(self, string, prependTimestamp=False):
        if prependTimestamp is True:
            lines = string.splitlines()
            curr_line_timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            for line in lines:
                print("[%s] %s" % (curr_line_timestamp, line), file=self)
        else:
            self.fd.write(string)

    def writelines(self, __lines):
        for line in __lines:
            self.write(line)

    def close(self):
        self.fd.close()

    def waitForFile(self, maxTries=5):
        """Waits for a file to exist."""
        tries = 0
        while tries < maxTries:
            if os.path.exists(self.filepath):
                return
            tries += 1
            time.sleep(0.5 * tries)
        raise IOError("Failed to create %s" % self.filepath)
