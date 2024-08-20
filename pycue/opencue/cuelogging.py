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


"""Module for reading and writing log files"""

import logging
import os
import platform
import datetime
import time

log = logging.getLogger(__name__)

class CueLogWriter(object):
    """Class to abstract file log writing, this class tries to act as a file object"""
    filepath = None
    def __init__(self, filepath, maxLogFiles=1):
        """CueLogWriter class initialization
           @type    filepath: string
           @param   filepath: The filepath to log to
           @type    maxLogFiles: int
           @param   maxLogFiles: number of files to rotate, when in write mode
        """

        self.filepath = filepath
        self.__log_dir = os.path.dirname(self.filepath)
        self.__maxLogFiles = maxLogFiles
        if not os.access(self.__log_dir, os.F_OK):
            self.__makeLogDir()

        if not os.access(self.__log_dir, os.W_OK):
            err = "Unable to write to log directory %s" % self.__log_dir
            raise RuntimeError(err)

        self.__attemptRotateLogs()
        # pylint: disable=consider-using-with
        self.__fd = open(self.filepath, "w+", 1, encoding='utf-8')
        try:
            os.chmod(self.filepath, 0o666)
        # pylint: disable=broad-except
        except Exception as e:
            err = "Failed to chmod log file! %s due to %s" % (self.filepath, e)
            log.warning(err)

    def __attemptRotateLogs(self):
        try:
            # Rotate any old logs to a max of MAX_LOG_FILES:
            if os.path.isfile(self.filepath):
                rotateCount = 1
                while (os.path.isfile("%s.%s" % (self.filepath, rotateCount))
                       and rotateCount < self.__maxLogFiles):
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

    def __makeLogDir(self):
        # Attempting mkdir for missing logdir
        msg = "No Error"
        try:
            os.makedirs(self.__log_dir)
            os.chmod(self.__log_dir, 0o777)
        # pylint: disable=broad-except
        except Exception as e:
            # This is expected to fail when called in abq
            # But the directory should now be visible
            msg = e

        if not os.access(self.__log_dir, os.F_OK):
            err = "Unable to see log directory: %s, mkdir failed with: %s" % (self.__log_dir, msg)
            raise RuntimeError(err)

    # pylint: disable=arguments-differ
    def write(self, data, prependTimestamp=False):
        """Abstract write function that will write to the correct backend"""
        # Convert data to unicode
        if isinstance(data, bytes):
            data = data.decode('utf-8', errors='ignore')
        if prependTimestamp is True:
            lines = data.splitlines()
            curr_line_timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            for line in lines:
                print("[%s] %s" % (curr_line_timestamp, line), file=self)
        else:
            self.__fd.write(data)

    def writelines(self, __lines):
        """Provides support for writing mutliple lines at a time"""
        for line in __lines:
            self.write(line)

    def close(self):
        """Closes the file if the backend is file based"""
        self.__fd.close()

    def waitForFile(self, maxTries=5):
        """Waits for the file to exist before continuing when using a file backend"""
        # Waits for a file to exist
        tries = 0
        while tries < maxTries:
            if os.path.exists(self.filepath):
                return
            tries += 1
            time.sleep(0.5 * tries)
        raise IOError("Failed to create %s" % self.filepath)


class CueLogReader(object):
    """Class to abstract file log reading, this class tries to act as a file object"""

    def __init__(self, filepath):
        """CueLogWriter class initialization
           @type    filepath: string
           @param   filepath: The filepath to log to
        """
        self.__filepath = filepath
        self.__fd = open(self.__filepath, "r", encoding='utf-8')

    def size(self):
        """Return the size of the file"""
        return int(os.stat(self.__filepath).st_size)

    def getMtime(self):
        """Return modification time of the file"""
        return os.path.getmtime(self.__filepath)

    def exists(self):
        """Check if the file exists"""
        return os.path.exists(self.__filepath)

    def read(self):
        """Read the data from the backend"""

        content = None
        if self.exists() is True:
            with open(self.__filepath, "r", encoding='utf-8') as fp:
                content = fp.read()

        return content

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
