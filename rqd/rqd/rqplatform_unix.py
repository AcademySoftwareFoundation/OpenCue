#  Copyright (c) OpenCue Project Authors
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

from . import rqconstants
from . import rqplatform_base
from . import rqutil

import logging as log
import math
import socket
import subprocess
import sys
import time
import traceback


KILOBYTE = 1024


class UnixPlatform(rqplatform_base.Platform):
    """Base for shared implementations between Linux/Darwin."""

    def __init__(self, pathCpuInfo=None):  # type: (Optional[str]) -> None
        self.__pathCpuInfo = pathCpuInfo or rqconstants.PATH_CPUINFO

    def getHostname(self):  # type: () -> str
        if rqconstants.RQD_USE_IP_AS_HOSTNAME:
            return rqutil.getHostIp()
        else:
            return socket.gethostbyaddr(socket.gethostname())[0].split('.')[0]

    def _getGpuValues(self):
        if not hasattr(self, 'gpuNotSupported'):
            if not hasattr(self, 'gpuResults'):
                self.gpuResults = {'total': 0, 'free': 0, 'updated': 0}
            if rqconstants.ALLOW_PLAYBLAST and not rqconstants.ALLOW_GPU:
                return {'total': 262144, 'free': 262144, 'updated': 0}
            if not rqconstants.ALLOW_GPU:
                self.gpuNotSupported = True
                return self.gpuResults
            if self.gpuResults['updated'] > time.time() - 60:
                return self.gpuResults
            try:
                # /shots/spi/home/bin/spinux1/cudaInfo
                # /shots/spi/home/bin/rhel7/cudaInfo
                cudaInfo = subprocess.getoutput('/usr/local/spi/rqd3/cudaInfo')
                if 'There is no device supporting CUDA' in cudaInfo:
                    self.gpuNotSupported = True
                else:
                    results = cudaInfo.splitlines()[-1].split()
                    #  TotalMem 1023 Mb  FreeMem 968 Mb
                    # The int(math.ceil(int(x) / 32.0) * 32) rounds up to the next multiple of 32
                    self.gpuResults['total'] = int(math.ceil(int(results[1]) / 32.0) * 32) * KILOBYTE
                    self.gpuResults['free'] = int(results[4]) * KILOBYTE
                    self.gpuResults['updated'] = time.time()
            except Exception as e:
                log.warning('Failed to get FreeMem from cudaInfo due to: %s at %s' % \
                            (e, traceback.extract_tb(sys.exc_info()[2])))
        return self.gpuResults

    def getCpuInfo(self):  # type: () -> rqplatform_base.CpuInfo
        totalCores = 0
        numProcs = 0
        hyperthreadingMultiplier = 1

        # Reads static information from /proc/cpuinfo
        with open(self.__pathCpuInfo, "r") as cpuinfoFile:
            singleCore = {}
            procsFound = []
            for line in cpuinfoFile:
                lineList = line.strip().replace("\t", "").split(": ")
                # A normal entry added to the singleCore dictionary
                if len(lineList) >= 2:
                    singleCore[lineList[0]] = lineList[1]
                # The end of a processor block
                elif lineList == ['']:
                    # Check for hyper-threading
                    hyperthreadingMultiplier = (int(singleCore.get('siblings', '1'))
                                                // int(singleCore.get('cpu cores', '1')))

                    totalCores += 1
                    if "core id" in singleCore \
                            and "physical id" in singleCore \
                            and not singleCore["physical id"] in procsFound:
                        procsFound.append(singleCore["physical id"])
                        numProcs += 1
                    elif "core id" not in singleCore:
                        numProcs += 1
                    singleCore = {}
                # An entry without data
                elif len(lineList) == 1:
                    singleCore[lineList[0]] = ""

        return rqplatform_base.CpuInfo(totalCores, numProcs, hyperthreadingMultiplier)
