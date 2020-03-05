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

from abc import ABCMeta, abstractmethod
import os
import psutil
import tempfile


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


class Platform(object):
    """Abstracts over platform-specific functionality."""

    __metaclass__ = ABCMeta

    # Note that these two functions are no longer platform-specific,
    # but we have them here for consistency with the other operations:
    def getTempPath(self):  # type: () -> str
        """Returns the correct mcp path for the given machine"""
        if os.path.isdir("/mcp/"):
            return "/mcp/"
        
        # make sure path ends with directory separator,
        # this will add one if it is not already present:
        return os.path.join(tempfile.gettempdir(), '')

    def getDiskInfo(self):  # type: () -> DiskInfo
        tmp = self.getTempPath()
        usage = psutil.disk_usage(tmp)
        return DiskInfo(total_mcp=(usage.total // 1024), free_mcp=(usage.free // 1024))

    @abstractmethod
    def getHostname(self):  # type: () -> str
        pass

    @abstractmethod
    def getMemoryInfo(self):  # type: () -> MemoryInfo
        pass

    @abstractmethod
    def getCpuInfo(self):  # type: () -> CpuInfo
        pass

    @abstractmethod
    def getBootTime(self):  # type: () -> int
        pass

    @abstractmethod
    def getLoadAvg(self):  # type: () -> int
        pass
