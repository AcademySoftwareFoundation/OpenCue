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

import ctypes
import psutil
import socket

from . import rqplatform_base


# From http://stackoverflow.com/questions/2017545/get-memory-usage-of-computer-in-windows-with-python
class MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [("dwLength", ctypes.c_uint),
                ("dwMemoryLoad", ctypes.c_uint),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("sullAvailExtendedVirtual", ctypes.c_ulonglong), ]

    def __init__(self):
        # have to initialize this to the size of MEMORYSTATUSEX
        self.dwLength = 2 * 4 + 7 * 8  # size = 2 ints, 7 longs
        super(MEMORYSTATUSEX, self).__init__()


def _getWindowsProcessorCount():
    """Counts the actual number of physical CPUs on Windows"""

    # see: https://docs.microsoft.com/en-nz/windows/win32/api/winnt/ns-winnt-system_logical_processor_information_ex
    class SYSTEM_LOGICAL_PROCESSOR_INFORMATION_EX(ctypes.Structure):
        _fields_ = [
            ("Relationship", ctypes.c_int),
            ("Size", ctypes.c_ulong),
            # ignore other fields, we don't need them
        ]

    # see: https://docs.microsoft.com/en-nz/windows/win32/api/sysinfoapi/nf-sysinfoapi-getlogicalprocessorinformationex
    glpie = ctypes.windll.kernel32.GetLogicalProcessorInformationEx
    glpie.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_byte), ctypes.POINTER(ctypes.c_ulong)]
    glpie.restype = ctypes.c_int  # Win32 BOOL is an int

    # find required buffer size by invoking with NULL buffer:
    buffer_size = ctypes.c_ulong(0)
    relationship_type = 3  # 3 == RelationProcessorPackage
    if glpie(relationship_type, None, ctypes.byref(buffer_size)) == 1:
        raise RuntimeError("Expected to get a failure!")
    else:
        if ctypes.GetLastError() != 122:
            # 122 = ERROR_INSUFFICIENT_BUFFER, which is expected for this call
            raise RuntimeError(ctypes.FormatError())

    # allocate required buffer size & re-invoke:
    buffer = (ctypes.c_byte * buffer_size.value)()
    if glpie(relationship_type, buffer, ctypes.byref(buffer_size)) == 0:
        raise RuntimeError(ctypes.FormatError())

    # count the items in the resulting array; this will be the number of physical processors:
    offset = 0
    num_procs = 0
    while offset < buffer_size.value:
        num_procs += 1
        proc_info = SYSTEM_LOGICAL_PROCESSOR_INFORMATION_EX.from_buffer(buffer, offset)
        offset += proc_info.Size

    return num_procs


class WindowsPlatform(rqplatform_base.Platform):
    def __init__(self):
        self.__windowsStat = MEMORYSTATUSEX()
        self.__socketCount = _getWindowsProcessorCount()

    def getHostname(self):  # type: () -> str
        return socket.gethostname()

    def getMemoryInfo(self):  # type: () -> rqplatform_base.MemoryInfo
        stats = MEMORYSTATUSEX()
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stats))

        return rqplatform_base.MemoryInfo(
            total_mem=int(stats.ullTotalPhys / 1024),
            free_mem=int(stats.ullAvailPhys / 1024),
            total_swap=int(stats.ullTotalPageFile / 1024),
            free_swap=int(stats.ullAvailPageFile / 1024),
            free_gpu=0,  # TODO: GPU memory, https://github.com/AcademySoftwareFoundation/OpenCue/issues/61
            total_gpu=0,  # TODO: GPU memory, https://github.com/AcademySoftwareFoundation/OpenCue/issues/61
            swap_out=0,
        )

    def getCpuInfo(self):  # type: () -> rqplatform_base.CpuInfo
        total_cores = psutil.cpu_count(logical=True)
        physical_cores = psutil.cpu_count(logical=False)
        hyperthreading_multiplier = total_cores // physical_cores

        return rqplatform_base.CpuInfo(
            total_cores,
            self.__socketCount,
            hyperthreading_multiplier)

    def getLoadAvg(self):  # type: () -> int
        return 0  # TODO: https://github.com/AcademySoftwareFoundation/OpenCue/issues/61

    def getBootTime(self): # type: () -> int
        return 0  # TODO: https://github.com/AcademySoftwareFoundation/OpenCue/issues/61
