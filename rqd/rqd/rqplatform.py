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

from abc import ABC, abstractmethod
import logging as log
import os
import platform
import shutil
import tempfile

from . import rqconstants


class CpuInfo(object):
    """Contains static CPU information."""
    def __init__(self, logical_cores, physical_cpus, hyperthreading_multiplier):
        self.logical_cores = logical_cores
        self.physical_cpus = physical_cpus
        self.hyperthreading_multiplier = hyperthreading_multiplier


class DiskInfo(object):
    """Contains dynamic disk space for temp path, in kilobytes."""
    def __init__(self, total_mcp, free_mcp):
        self.total_mcp = total_mcp
        self.free_mcp = free_mcp


class MemoryInfo(object):
    """Contains static and dynamic information about memory usage, in bytes."""
    def __init__(self, total_mem, free_mem, total_swap, free_swap, total_gpu, free_gpu, swap_out):
        self.total_mem = total_mem
        self.free_mem = free_mem
        self.total_swap = total_swap
        self.free_swap = free_swap
        self.total_gpu = total_gpu
        self.free_gpu = free_gpu
        self.swap_out = swap_out


class Platform(ABC):
    """Abstracts over platform-specific functionality."""

    # Note that these two functions are no longer platform-specific,
    # but we have them here for consistency with the other operations:
    def getTempPath(self) -> str:
        """Returns the correct mcp path for the given machine"""
        if os.path.isdir("/mcp/"):
            return "/mcp/"
        return '%s/' % tempfile.gettempdir()

    def getDiskInfo(self) -> DiskInfo:
        tmp = self.getTempPath()
        total, used, free = shutil.disk_usage(tmp)
        return DiskInfo(total_mcp=(total // 1024), free_mcp=(free // 1024))

    @abstractmethod
    def getHostname(self) -> str: ...

    @abstractmethod
    def getMemoryInfo(self) -> MemoryInfo: ...

    @abstractmethod
    def getCpuInfo(self) -> CpuInfo: ...

    @abstractmethod
    def getBootTime(self) -> int: ...

    @abstractmethod
    def getLoadAvg(self) -> int: ...


class ApplyConfigOverrides(Platform):
    """Overrides specific values with values from the configuration:"""
    def __init__(self, inner: Platform):
        self.__inner = inner

    def getMemoryInfo(self) -> MemoryInfo:
        mem_info = self.__inner.getMemoryInfo()

        if rqconstants.OVERRIDE_MEMORY is not None:
            log.warning("Manually overriding the total memory")
            mem_info.total_mem = rqconstants.OVERRIDE_MEMORY

        return mem_info

    def getCpuInfo(self) -> CpuInfo:
        cpu_info = self.__inner.getCpuInfo()

        if rqconstants.OVERRIDE_CORES is not None:
            log.warning("Manually overriding the number of reported cores")
            cpu_info.logical_cores = rqconstants.OVERRIDE_CORES

        if rqconstants.OVERRIDE_PROCS is not None:
            log.warning("Manually overriding the number of reported procs")
            cpu_info.physical_cpus = rqconstants.OVERRIDE_PROCS

        return cpu_info

    def getHostname(self) -> str:
        return self.__inner.getHostname()

    def getLoadAvg(self) -> int:
        return self.__inner.getLoadAvg()

    def getBootTime(self) -> int:
        return self.__inner.getBootTime()


# define a globally-accessible instance:
def create_platform() -> Platform:

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


current_platform = create_platform()