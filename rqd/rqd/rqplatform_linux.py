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
from . import rqplatform_unix
from . import rqswap


KILOBYTE = 1024


class LinuxPlatform(rqplatform_unix.UnixPlatform):

    def __init__(self, pathCpuInfo=None):  # type: (Optional[str]) -> None
        super(LinuxPlatform, self).__init__(pathCpuInfo)

        self.__vmstat = rqswap.VmStat()

        cpuInfo = super(LinuxPlatform, self).getCpuInfo()
        self.__hyperthreadingMultiplier = cpuInfo.hyperthreading_multiplier

    def getMemoryInfo(self):  # type: () -> rqplatform_base.MemoryInfo
        total_mem = 0
        freeMem = 0
        totalSwapMem = 0
        freeSwapMem = 0
        cachedMem = 0

        # Reads dynamic information from /proc/meminfo:
        with open(rqconstants.PATH_MEMINFO, "r") as fp:
            for line in fp:
                if line.startswith("MemFree"):
                    freeMem = int(line.split()[1])
                elif line.startswith("SwapTotal"):
                    totalSwapMem = int(line.split()[1])
                elif line.startswith("SwapFree"):
                    freeSwapMem = int(line.split()[1])
                elif line.startswith("Cached"):
                    cachedMem = int(line.split()[1])
                elif line.startswith("MemTotal"):
                    total_mem = int(line.split()[1])

        gpu_values = self._getGpuValues()

        return rqplatform_base.MemoryInfo(
            total_mem=total_mem,
            free_mem=freeMem + cachedMem,
            total_swap=totalSwapMem,
            free_swap=freeSwapMem,
            total_gpu=gpu_values['total'],
            free_gpu=gpu_values['free'],
            swap_out=self.__getSwapout())

    def __getSwapout(self):
        try:
            return str(int(self.__vmstat.getRecentPgoutRate()))
        except:
            return str(0)

    def getLoadAvg(self):  # type: () -> int
        loadAvgFile = open(rqconstants.PATH_LOADAVG, "r")
        loadAvg = int(float(loadAvgFile.read().split()[0]) * 100)
        loadAvg = loadAvg // self.__hyperthreadingMultiplier
        loadAvg = loadAvg + rqconstants.LOAD_MODIFIER
        loadAvg = max(loadAvg, 0)
        return loadAvg

    def getBootTime(self):  # type: () -> int
        statFile = open(rqconstants.PATH_STAT, "r")
        for line in statFile:
            if line.startswith("btime"):
                return int(line.split()[1])
