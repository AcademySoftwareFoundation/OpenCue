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

from __future__ import annotations
import abc
import logging
import time
import os
import datetime
import platform
from abc import ABC

import rqd.rqconstants

log = logging.getLogger(__name__)
log.setLevel(rqd.rqconstants.CONSOLE_LOG_LEVEL)


class RqdLogger:
    """Class to abstract file logging, this class tries to act as a file object"""
    filepath = None
    fd = None
    type = 0

    def __init__(self, filepath):
        """RQDLogger class initialization
           @type    filepath: string
           @param   filepath: The filepath to log to
        """
        self._strategy = _make_strategy(self)
        self.filepath = filepath

        log_dir = os.path.dirname(self.filepath)
        if not os.access(log_dir, os.F_OK):
            # Attempting mkdir for missing logdir
            msg = "No Error"
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

        # Rotate any old logs to a max of MAX_LOG_FILES
        if os.path.isfile(self.filepath):
            self._strategy.rotateLogFile()

        # pylint: disable=consider-using-with
        self.fd = open(self.filepath, "w+", 1, encoding='utf-8')
        try:
            os.chmod(self.filepath, 0o666)
        # pylint: disable=broad-except
        except Exception as e:
            err = "Failed to chmod log file! %s due to %s" % (self.filepath, e)
            log.warning(err)

    # pylint: disable=arguments-differ
    def write(self, data, prependTimestamp=False):
        """Abstract write function that will write to the correct backend"""
        # Convert data to unicode
        if isinstance(data, bytes):
            data = data.decode("utf-8", errors="ignore")
        if prependTimestamp is True:
            lines = data.splitlines()
            curr_line_timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            for line in lines:
                print("[%s] %s" % (curr_line_timestamp, line), file=self)
        else:
            self.fd.write(data)

    def writelines(self, __lines):
        """Provides support for writing mutliple lines at a time"""
        for line in __lines:
            self.write(line)

    def close(self):
        """Closes the file if the backend is file based"""
        self.fd.close()

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

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class LokiLogger:
    """Class for logging to a loki server. It mimics a file object as much as possible"""
    def __init__(self, lokiURL, runFrame):
        try:
            # pylint: disable=import-outside-toplevel
            from loki_urllib3_client import LokiClient
        except ImportError:
            return
        self.client = LokiClient(url=lokiURL)
        self.runFrame = runFrame
        self.sessionStartTime = datetime.datetime.now().timestamp()
        self.defaultLogData = {
            'host': platform.node(),
            'job_name': self.runFrame.job_name,
            'frame_name': self.runFrame.frame_name,
            'username': self.runFrame.user_name,
            'frame_id': self.runFrame.frame_id,
            'session_start_time': str(self.sessionStartTime)
        }

    def waitForFile(self, maxTries=5):
        """Waits for the connection to be ready before continuing"""
        tries = 0
        while tries < maxTries:
            if self.client.ready() is True:
                return
            tries += 1
            time.sleep(0.5 * tries)
        raise IOError("Failed to create loki stream")

    # pylint: disable=unused-argument
    def write(self, data, prependTimestamp=False):
        """
        Provides write function for writing to loki server.
        Ignores prepentTimeStamp which is redundant with Loki
        """
        if len(data.strip()) == 0:
            return
        if isinstance(data, bytes):
            data = data.decode('utf-8', errors='ignore')
        requestStatus, requestCode = self.client.post(self.defaultLogData, [data.strip()])
        if requestStatus is not True:
            raise IOError(f"Failed to write log to loki server with error : {requestCode}")

    def writelines(self, __lines):
        """Provides support for writing mutliple lines at a time"""
        for line in __lines:
            self.write(line)

    def close(self):
        """Dummy function since cloasing it not necessary for the http connection"""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class _RqgLoggerStrategy(ABC):
    """Abstract base class for RqdLogger strategies for different platforms."""

    def __init__(self, rqdLogger: RqdLogger) -> None:
        """Initialize with the RqdLogger instance."""
        self.rqdLogger = rqdLogger

    @abc.abstractmethod
    def rotateLogFile(self) -> None:
        """Rotate the log file according to platform-specific logic."""

    def _rotateLogFile(self) -> None:
        """Common log rotation logic used by all platforms."""
        count = 1
        while (
            os.path.isfile("%s.%s" % (self.rqdLogger.filepath, count))
            and count < rqd.rqconstants.MAX_LOG_FILES
        ):
            count += 1
        os.rename(self.rqdLogger.filepath, "%s.%s" % (self.rqdLogger.filepath, count))


class WindowsRqdLoggerStrategy(_RqgLoggerStrategy):
    """Class to handle Windows-specific logging logic."""

    ROTATION_MAX_RETRIES = 3

    def rotateLogFile(self):
        """Rotate log file with Windows-specific handling for file locks"""
        # On Windows, try multiple times with delays for UNC paths
        for attempt in range(self.ROTATION_MAX_RETRIES):
            try:
                self._rotateLogFile()
            except OSError as e:
                if attempt < self.ROTATION_MAX_RETRIES - 1:
                    # Wait a bit and retry
                    time.sleep(0.1)
                    continue
                # Windows might fail while trying to rotate logs for checking if file is
                # being used by another process. Frame execution doesn't need to
                # be halted for this.
                err = "Unable to rotate previous log file due to %s" % e
                log.debug(err)
                return
            else:
                # Success
                return


class LinuxRqdLoggerStrategy(_RqgLoggerStrategy):
    """Class to handle Linux-specific logging logic"""

    def rotateLogFile(self) -> None:
        """Rotate log file with Linux-specific handling.

        @Raises RuntimeError: If log rotation fails.
        """
        try:
            self._rotateLogFile()
        # pylint: disable=broad-except
        except Exception as e:
            err = "Unable to rotate previous log file due to %s" % e
            raise RuntimeError(err)


def _make_strategy(rqdLogger: RqdLogger) -> _RqgLoggerStrategy:
    """Factory method to get the appropriate strategy based on platform."""
    if platform.system() == "Windows":
        return WindowsRqdLoggerStrategy(rqdLogger)
    return LinuxRqdLoggerStrategy(rqdLogger)
