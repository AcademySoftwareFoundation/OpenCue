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


import os
import unittest

import rqd.rqcore
import rqd.rqmachine
import rqd.compiled_proto.report_pb2


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
