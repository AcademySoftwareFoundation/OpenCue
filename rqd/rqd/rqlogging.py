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


import logging
import re
import time
import os
import datetime

from multiprocessing import Queue

import logging_loki

LOGTYPE_FILE = 1
LOGTYPE_LOKI = 2


class RQDLogger(object):
    """Class to abstract file logging, this class tries to act as a file object"""
    filepath = None
    fd = None
    type = 0

    def __init__(self, filepath):
        """RQDLogger class initialization
           @type    filepath: string
           @param   filepath: The filepath to log to
        """
        protocolMatch = re.match(r"(?P<proto>\w+)://(?P<filepath>.*)", filepath)
        if protocolMatch is not None:
            if protocolMatch.group('proto') == 'loki':
                self.type = LOGTYPE_LOKI
            self.filepath = protocolMatch.group('filepath')
        else:
            self.type = LOGTYPE_FILE
            self.filepath = filepath

        if self.type == LOGTYPE_LOKI:
            self.handler = logging_loki.LokiQueueHandler(
                Queue(-1),
                url="http://localhost:3100/loki/api/v1/push",
                tags={"application": "rqd",
                      "filepath": self.filepath},
                version="1",
            )
            self.logger = logging.getLogger("loki-logger")
            self.logger.setLevel(logging.INFO)
            self.logger.propagate = False
            self.logger.addHandler(self.handler)
        elif self.type == LOGTYPE_FILE:
            self.fd = open(self.filepath, "w+", 1)
        else:
            raise Exception("Unknown file path type")

    # pylint: disable=arguments-differ
    def write(self, data, prependTimestamp=False):
        if prependTimestamp is True:
            lines = data.splitlines()
            curr_line_timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            for line in lines:
                print("[%s] %s" % (curr_line_timestamp, line), file=self)
        else:
            if self.type == LOGTYPE_FILE:
                self.fd.write(data)
            elif self.type == LOGTYPE_FILE:
                # print() adds a newline in the end when writing to files.
                # Ignore this when not writing to files
                if data != os.linesep:
                    self.logger.info(data)

    def writelines(self, __lines):
        for line in __lines:
            self.write(line)

    def close(self):
        if self.type == LOGTYPE_FILE:
            self.fd.close()

    def waitForFile(self, maxTries=5):
        if self.type == LOGTYPE_FILE:
            """Waits for a file to exist."""
            tries = 0
            while tries < maxTries:
                if os.path.exists(self.filepath):
                    return
                tries += 1
                time.sleep(0.5 * tries)
            raise IOError("Failed to create %s" % self.filepath)
