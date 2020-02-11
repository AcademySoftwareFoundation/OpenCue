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


import logging as log
import platform

from . import rqconstants
from . import rqplatform_base


class ApplyConfigOverrides(rqplatform_base.Platform):
    """Overrides specific values with values from the configuration:"""
    def __init__(self, inner):  # type: (rqplatform_base.Platform) -> ApplyConfigOverrides
        self.__inner = inner

    def getMemoryInfo(self):  # type: () -> rqplatform_base.MemoryInfo
        mem_info = self.__inner.getMemoryInfo()

        if rqconstants.OVERRIDE_MEMORY is not None:
            log.warning("Manually overriding the total memory")
            mem_info.total_mem = rqconstants.OVERRIDE_MEMORY

        return mem_info

    def getCpuInfo(self):  # type: () -> rqplatform_base.CpuInfo
        cpu_info = self.__inner.getCpuInfo()

        if rqconstants.OVERRIDE_CORES is not None:
            log.warning("Manually overriding the number of reported cores")
            cpu_info.logical_cores = rqconstants.OVERRIDE_CORES

        if rqconstants.OVERRIDE_PROCS is not None:
            log.warning("Manually overriding the number of reported procs")
            cpu_info.physical_cpus = rqconstants.OVERRIDE_PROCS

        return cpu_info

    def getHostname(self):  # type: () -> str
        return self.__inner.getHostname()

    def getLoadAvg(self):  # type: () -> int
        return self.__inner.getLoadAvg()

    def getBootTime(self):  # type: () -> int
        return self.__inner.getBootTime()


def create_platform():  # type: () -> rqplatform_base.Platform
    """
    Create an appropriate Platform instance for the current platform,
    with overrides from the config applied.
    """

    system = platform.system()
    if system == 'Windows':
        from . import rqplatform_windows
        result = rqplatform_windows.WindowsPlatform()
    elif system == 'Darwin':
        from . import rqplatform_darwin
        result = rqplatform_darwin.DarwinPlatform()
    elif system == 'Linux':
        from . import rqplatform_linux
        result = rqplatform_linux.LinuxPlatform()
    else:
        raise RuntimeError("Unsupported platform: %s" % platform.system())

    return ApplyConfigOverrides(result)