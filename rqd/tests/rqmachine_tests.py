#!/usr/bin/env python

#  Copyright (c) 2018 Sony Pictures Imageworks Inc.
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


import mock
import os
import unittest

import rqd.rqcore
import rqd.rqmachine
import rqd.compiled_proto.report_pb2


MEMINFO = """MemTotal:       32942144 kB
MemFree:         5339060 kB
MemAvailable:   29191460 kB
Buffers:         1266484 kB
Cached:         20360116 kB
SwapCached:         6064 kB
Active:         10861012 kB
Inactive:       13918544 kB
Active(anon):    1807696 kB
Inactive(anon):  1086584 kB
Active(file):    9053316 kB
Inactive(file): 12831960 kB
Unevictable:        9544 kB
Mlocked:            9544 kB
SwapTotal:       4194300 kB
SwapFree:        4105212 kB
Dirty:              1120 kB
Writeback:             0 kB
AnonPages:       2916596 kB
Mapped:          1084660 kB
Shmem:              4456 kB
Slab:            2652808 kB
SReclaimable:    2415168 kB
SUnreclaim:       237640 kB
KernelStack:       26416 kB
PageTables:        21296 kB
NFS_Unstable:          0 kB
Bounce:                0 kB
WritebackTmp:          0 kB
CommitLimit:    20665372 kB
Committed_AS:   10363976 kB
VmallocTotal:   34359738367 kB
VmallocUsed:           0 kB
VmallocChunk:          0 kB
Percpu:             8768 kB
HardwareCorrupted:     0 kB
AnonHugePages:   1286144 kB
ShmemHugePages:        0 kB
ShmemPmdMapped:        0 kB
HugePages_Total:       0
HugePages_Free:        0
HugePages_Rsvd:        0
HugePages_Surp:        0
Hugepagesize:       2048 kB
Hugetlb:               0 kB
DirectMap4k:      479100 kB
DirectMap2M:    24686592 kB
DirectMap1G:    10485760 kB
"""


class StatvfsMock(mock.MagicMock):
    def __init__(self, *args, **kwargs):
        super(StatvfsMock, self).__init__(args, kwargs)
        self.f_bsize = 1048576
        self.f_frsize = 4096
        self.f_blocks = 360540255
        self.f_bfree = 285953527
        self.f_bavail = 267639130
        self.f_files = 91578368
        self.f_ffree = 91229495
        self.f_favail = 91229495
        self.f_flag = 4096
        self.f_namemax = 255


class MachineTests(unittest.TestCase):
    @staticmethod
    def __statvfs_mock():
        statvfs_mock = mock.Mock()
        statvfs_mock.f_bsize = 1048576
        statvfs_mock.f_frsize = 4096
        statvfs_mock.f_blocks = 360540255
        statvfs_mock.f_bfree = 285953527
        statvfs_mock.f_bavail = 267639130
        statvfs_mock.f_files = 91578368
        statvfs_mock.f_ffree = 91229495
        statvfs_mock.f_favail = 91229495
        statvfs_mock.f_flag = 4096
        statvfs_mock.f_namemax = 255
        return statvfs_mock

    @mock.patch('__builtin__.open', new=mock.mock_open(read_data=MEMINFO))
    @mock.patch('os.statvfs')
    @mock.patch.object(rqd.rqmachine.Machine, 'getBootTime', new=mock.MagicMock(return_value=9876))
    @mock.patch('rqd.rqutil.getHostname', new=mock.MagicMock(return_value='arbitrary-hostname'))
    @mock.patch('platform.system', new=mock.MagicMock(return_value='Linux'))
    def test_isNimbySafeToRunJobs(self, statvfsMock):
        statvfs_mock = mock.MagicMock()
        statvfs_mock.f_bsize = 1048576
        statvfs_mock.f_frsize = 4096
        statvfs_mock.f_blocks = 360540255
        statvfs_mock.f_bfree = 285953527
        statvfs_mock.f_bavail = 267639130
        statvfs_mock.f_files = 91578368
        statvfs_mock.f_ffree = 91229495
        statvfs_mock.f_favail = 91229495
        statvfs_mock.f_flag = 4096
        statvfs_mock.f_namemax = 255
        statvfsMock.return_value = statvfs_mock

        rqCore = mock.MagicMock(spec=rqd.rqcore.RqCore)
        coreDetail = rqd.compiled_proto.report_pb2.CoreDetail()

        machine = rqd.rqmachine.Machine(rqCore, coreDetail)
        print machine.isNimbySafeToRunJobs()


class CpuinfoTests(unittest.TestCase):

    def setUp(self):
        self.rqd = rqd.rqcore.RqCore()
    
    def test_shark(self):
        self.__cpuinfoTestHelper('_cpuinfo_shark_ht_8-4-2-2')
        
    def test_shark_ht(self):
        self.__cpuinfoTestHelper('_cpuinfo_shark_8-4-2')

    def test_dub(self):
        self.__cpuinfoTestHelper('_cpuinfo_dub_8-4-2')

    def test_drack(self):
        self.__cpuinfoTestHelper('_cpuinfo_drack_4-2-2')

    def test_genosis(self):
        self.__cpuinfoTestHelper('_cpuinfo_genosis_1-1-1')

    def test_rider(self):
        self.__cpuinfoTestHelper('_cpuinfo_rider_4-2-2')

    def test_vrack(self):
        self.__cpuinfoTestHelper('_cpuinfo_vrack_2-1-2')

    def test_8600(self):
        self.__cpuinfoTestHelper('_cpuinfo_hp8600_8-4-2')

    def test_dub(self):
        self.__cpuinfoTestHelper('_cpuinfo_dub_8-4-2')

    def test_srdsvr05(self):
        self.__cpuinfoTestHelper('_cpuinfo_srdsvr05_ht_12-6-2-2')

    def test_srdsvr09(self):
        self.__cpuinfoTestHelper('_cpuinfo_srdsvr09_48-12-4')

    def __cpuinfoTestHelper(self, pathCpuInfo):
        # File format: _cpuinfo_dub_x-x-x where x-x-x is totalCores-coresPerProc-numProcs
        pathCpuInfo = os.path.join(os.path.dirname(__file__), 'cpuinfo', pathCpuInfo)
        renderHost, coreInfo = self.rqd.machine.testInitMachineStats(pathCpuInfo)
        totalCores, coresPerProc, numProcs = pathCpuInfo.split('_')[-1].split('-')[:3]
        self.assertEqual(renderHost.num_procs, int(numProcs))
        self.assertEqual(renderHost.cores_per_proc, int(coresPerProc) * 100)
        self.assertEqual(coreInfo.total_cores, int(totalCores) * 100)
        self.assertEqual(coreInfo.idle_cores, int(totalCores) * 100)
        self.assertEqual(coreInfo.locked_cores, 0)
        self.assertEqual(coreInfo.booked_cores, 0)
        if '_ht_' in pathCpuInfo:
            self.assertEqual(
                renderHost.attributes['hyperthreadingMultiplier'], pathCpuInfo.split('-')[3])


if __name__ == '__main__':
    unittest.main()
