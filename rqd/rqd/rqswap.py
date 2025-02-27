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


"""Utility classes and functions to get virtual memory page out number."""


from __future__ import with_statement
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

from builtins import str
from builtins import range
from builtins import object
import logging
import re
import threading
import time


log = logging.getLogger(__name__)
PGPGOUT_RE = re.compile(r"^pgpgout (\d+)")


class VmStatException(Exception):
    """Something for clients to catch if something goes wrong in here."""


class SampleData(object):
    """Sample data container."""

    def __init__(self, epochTime, pgoutNum):
        """
        Constructor.
        """
        self.__epochTimeInSecond = epochTime
        self.__pgpgout = pgoutNum

    def __repr__(self):
        """
        Return string representation.
        """
        return "(" + str(self.__epochTimeInSecond) + ", " + str(self.__pgpgout) + ")"

    def get_epoch_time(self):
        """
        Return the sample's epoch time.
        """
        return self.__epochTimeInSecond

    def get_pgout_number(self):
        """
        Return the sample's page out number.
        """
        return self.__pgpgout


class RepeatedTimer(threading.Thread):
    """
    A repeated timer.
    """

    def __init__(self, interval, function, *args, **kwargs):
        threading.Thread.__init__(self)
        self.__interval = interval
        self.__callable = function
        self.__args = args
        self.__kwargs = kwargs
        self.__event = threading.Event()
        self.__event.set()

    def run(self):
        while self.__event.is_set():
            try:
                timer = threading.Timer(self.__interval,
                                        self.__callable,
                                        self.__args,
                                        self.__kwargs)
                timer.start()
                timer.join()
            # pylint: disable=broad-except
            except Exception:
                # Catch all exceptions here.
                pass

    def cancel(self):
        """
        Cancel the repeated timer.
        """
        self.__event.clear()


class VmStat(object):
    """
    A simple class to return pgpgout number from /proc/vmstat.
    """

    def __init__(self):
        self.__interval = 15
        self.__sampleSize = 10
        self.__lock = threading.Lock()
        self.__sampleData = []
        self.__repeatedTimer = RepeatedTimer(
            self.__interval,
            self.__getPgoutNum)
        self.__repeatedTimer.daemon = True
        self.__repeatedTimer.start()

    def __getSampleDataCopy(self):
        with self.__lock:
            currentSampleData = list(self.__sampleData)
        return currentSampleData

    def __getPgoutNum(self):
        """
        Read /proc/vmstat file and get pgpgout number.
        """
        foundPgpgout = False
        pgpgoutNum = 0
        try:
            with open("/proc/vmstat", encoding='utf-8') as vmStatFile:
                for line in vmStatFile.readlines():
                    matchObj = PGPGOUT_RE.match(line)
                    if matchObj:
                        foundPgpgout = True
                        pgpgoutNum = int(matchObj.group(1))
                        break
        except IOError:
            log.warning("Failed to open /proc/vmstat file.")

        if foundPgpgout:
            with self.__lock:
                self.__sampleData.append(SampleData(time.time(),
                                                     pgpgoutNum))
                del self.__sampleData[:-self.__sampleSize]
        else:
            log.warning("Could not get pgpgout number.")

    def getPgoutRate(self):
        """Gets the pgout rate."""
        currentSampleData = self.__getSampleDataCopy()
        currentTime = time.time()
        sampleDataLen = len(currentSampleData)
        if sampleDataLen < 5:
            return 0

        weight = 1
        totalWeight = weight
        weightedSum = 0
        for i in range(1, sampleDataLen):
            if (currentSampleData[i].get_epoch_time() <
                    currentTime - self.__sampleSize * self.__interval - 2):
                continue
            weightedSum += (weight *
                            (currentSampleData[i].getPgoutNumber() -
                             currentSampleData[i - 1].getPgoutNumber()) /
                            (currentSampleData[i].getEpochTime() -
                             currentSampleData[i - 1].getEpochTime()))
            totalWeight += weight
            weight += 1

        return weightedSum / (totalWeight * self.__interval)

    def getRecentPgoutRate(self):
        """Gets the recent pgout rate."""
        currentSampleData = self.__getSampleDataCopy()
        sampleDataLen = len(currentSampleData)
        if sampleDataLen < 2:
            return 0

        index = sampleDataLen - 1
        return ((currentSampleData[index].getPgoutNumber() -
                 currentSampleData[index - 1].getPgoutNumber()) /
                (currentSampleData[index].getEpochTime() -
                 currentSampleData[index - 1].getEpochTime()) /
                self.__interval)

    def stopSample(self):
        """
        Stop the repeated timer.
        """
        self.__repeatedTimer.cancel()
