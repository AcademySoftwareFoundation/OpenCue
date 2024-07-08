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
import platform

import logging_loki

import rqd.rqconstants

LOGTYPE_FILE = 1
LOGTYPE_LOKI = 2

log = logging.getLogger(__name__)
log.setLevel(rqd.rqconstants.CONSOLE_LOG_LEVEL)

# This is to avoid a bug in logging_loki that generates debug messages in urllib3
logging.getLogger('urllib3').setLevel(logging.INFO)


class LokiLogger(object):
    """Class for loki specific logging"""
    def __init__(self, server, filepath, runFrame=None):
        startTime = str(time.time_ns())
        base_url = rqd.rqconstants.LOKI_SERVERS.get(server)
        endpoint = f"{base_url}/api/v1/push"
        handler = logging_loki.LokiHandler(
            url=endpoint,
            tags={"application": "rqd",
                  "filepath": filepath,
                  "start_time": startTime,
                  "job_name": runFrame.job_name or "",
                  "show": runFrame.show or "",
                  "shot": runFrame.shot or "",
                  "frame_name": runFrame.frame_name or "",
                  "user_name": runFrame.user_name or ""
                  },
            version="1",
        )
        self.logger = logging.getLogger(filepath)
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False
        self.logger.addHandler(handler)

    def info(self, data):
        """
        Function to log with info level
        """
        self.logger.info(data.strip())

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class RQDLogger(object):
    """Class to abstract file logging, this class tries to act as a file object"""
    filepath = None
    fd = None
    type = 0

    def __init__(self, filepath, runFrame=None):
        """RQDLogger class initialization
           @type    filepath: string
           @param   filepath: The filepath to log to
        """

        protocolMatch = re.match(r"(?P<proto>[\w\-.:]+)://(?P<server>\w+)/(?P<filepath>.*)",
                                 filepath)
        if protocolMatch is not None:
            if protocolMatch.group('proto') == 'loki':
                self.type = LOGTYPE_LOKI
            self.filepath = protocolMatch.group('filepath')
            self.server = protocolMatch.group('server')
        else:
            self.type = LOGTYPE_FILE
            self.filepath = filepath

        if self.type == LOGTYPE_LOKI:
            self.logger = LokiLogger(self.server, self.filepath, runFrame=runFrame)
        elif self.type == LOGTYPE_FILE:
            log_dir = os.path.dirname(self.filepath)
            if not os.access(log_dir, os.F_OK):
                # Attempting mkdir for missing logdir
                try:
                    os.makedirs(log_dir)
                    os.chmod(log_dir, 0o777)
                # pylint: disable=broad-except
                except Exception as e:
                    # This is expected to fail when called in abq
                    # But the directory should now be visible
                    msg = e

                if not os.access(log_dir, os.F_OK):
                    err = "Unable to see log directory: %s, mkdir failed with: %s" % (
                        log_dir, msg)
                    raise RuntimeError(err)

            if not os.access(log_dir, os.W_OK):
                err = "Unable to write to log directory %s" % log_dir
                raise RuntimeError(err)

            try:
                # Rotate any old logs to a max of MAX_LOG_FILES:
                if os.path.isfile(self.filepath):
                    rotateCount = 1
                    while (os.path.isfile("%s.%s" % (self.filepath, rotateCount))
                           and rotateCount < rqd.rqconstants.MAX_LOG_FILES):
                        rotateCount += 1
                    os.rename(self.filepath,
                              "%s.%s" % (self.filepath, rotateCount))
            # pylint: disable=broad-except
            except Exception as e:
                err = "Unable to rotate previous log file due to %s" % e
                # Windows might fail while trying to rotate logs for checking if file is
                # being used by another process. Frame execution doesn't need to
                # be halted for this.
                if platform.system() == "Windows":
                    log.warning(err)
                else:
                    raise RuntimeError(err)
            self.fd = open(self.filepath, "w+", 1)
            try:
                os.chmod(self.filepath, 0o666)
            # pylint: disable=broad-except
            except Exception as e:
                err = "Failed to chmod log file! %s due to %s" % (self.filepath, e)
                log.warning(err)
        else:
            raise Exception("Unknown file path type")

    # pylint: disable=arguments-differ
    def write(self, data, prependTimestamp=False):
        """Abstract write function that will write to the correct backend"""
        if prependTimestamp is True:
            lines = data.splitlines()
            curr_line_timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            for line in lines:
                print("[%s] %s" % (curr_line_timestamp, line), file=self)
        else:
            if self.type == LOGTYPE_FILE:
                self.fd.write(data)
            elif self.type == LOGTYPE_LOKI:
                # Popen adds a newline in the end when writing to files.
                # Ignore this when not writing to files
                if data != os.linesep:
                    self.logger.info(data)

    def writelines(self, __lines):
        """Provides support for writing mutliple lines at a time"""
        for line in __lines:
            self.write(line)

    def close(self):
        """Closes the file if the backend is file based"""
        if self.type == LOGTYPE_FILE:
            self.fd.close()
        elif self.type == LOGTYPE_LOKI:
            pass

    def waitForFile(self, maxTries=5):
        """Waits for the file to exist before continuing when using a file backend"""
        if self.type == LOGTYPE_FILE:
            # Waits for a file to exist
            tries = 0
            while tries < maxTries:
                if os.path.exists(self.filepath):
                    return
                tries += 1
                time.sleep(0.5 * tries)
            raise IOError("Failed to create %s" % self.filepath)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
