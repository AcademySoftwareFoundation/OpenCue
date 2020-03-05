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

from . import rqplatform_base
from . import rqplatform_unix

import re
import subprocess


class DarwinPlatform(rqplatform_unix.UnixPlatform):

    def __init__(self, pathCpuInfo=None):  # type: (Optional[str]) -> None
        super(DarwinPlatform, self).__init__(pathCpuInfo)

    def getMemoryInfo(self):  # type: () -> rqplatform_base.MemoryInfo
        memsizeOutput = subprocess.getoutput('sysctl hw.memsize').strip()
        memsizeRegex = re.compile(r'^hw.memsize: (?P<totalMemBytes>[\d]+)$')
        memsizeMatch = memsizeRegex.match(memsizeOutput)
        if memsizeMatch:
            total_mem = int(memsizeMatch.group('totalMemBytes')) // 1024
        else:
            total_mem = 0

        vmStatLines = subprocess.getoutput('vm_stat').split('\n')
        lineRegex = re.compile(r'^(?P<field>.+):[\s]+(?P<pages>[\d]+).$')
        vmStats = {}
        for line in vmStatLines[1:-2]:
            match = lineRegex.match(line)
            if match:
                vmStats[match.group('field')] = int(match.group('pages')) * 4096

        freeMemory = vmStats.get("Pages free", 0) // 1024
        inactiveMemory = vmStats.get("Pages inactive", 0) // 1024

        swapStats = subprocess.getoutput('sysctl vm.swapusage').strip()
        swapRegex = re.compile(r'^.* free = (?P<freeMb>[\d]+)M .*$')
        swapMatch = swapRegex.match(swapStats)
        if swapMatch:
            free_swap = int(float(swapMatch.group('freeMb')) * 1024)
        else:
            free_swap = 0

        gpu_values = self._getGpuValues()

        return rqplatform_base.MemoryInfo(
            total_mem=total_mem,
            free_mem=freeMemory + inactiveMemory,
            total_swap=0,  # TODO
            free_swap=free_swap,
            total_gpu=gpu_values['total'],
            free_gpu=gpu_values['free'],
            swap_out=0)  # TODO: https://github.com/AcademySoftwareFoundation/OpenCue/issues/193

    def getLoadAvg(self):  # type: () -> int
        return 0  # TODO: https://github.com/AcademySoftwareFoundation/OpenCue/issues/193

    def getBootTime(self):  # type: () -> int
        return 0  # TODO: https://github.com/AcademySoftwareFoundation/OpenCue/issues/193
