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

from __future__ import print_function
from __future__ import absolute_import
import os
import unittest

from .rqcore import RqCore

from .test.test_cuebot_listener import RqdReportStaticServer


class SetupCuebotListener(unittest.TestCase):
    def __init__(self):
        super(SetupCuebotListener, self).__init__()
        self.server = RqdReportStaticServer()
        self.servicer = self.server.servicer


class test_Machine_cpuinfo(unittest.TestCase):
    def setUp(self):
        #rqconstants.DISABLE_NIMBY = True
        self.rqd = RqCore()

    def tearDown(self):
        del self.rqd

    def _printme(self):
        print(len(self.rqd.machine.procDict))
        print(self.rqd.machine._procCount)
        print(self.rqd.machine._coreCount)
        print(self.rqd.machine._coresPerProc)

    def test_shark(self):
        self.__cpuinfoTestHelper('./test/_cpuinfo_shark_ht_8-4-2-2')

    def test_shark_ht(self):
        self.__cpuinfoTestHelper('./test/_cpuinfo_shark_8-4-2')

    def test_dub(self):
        self.__cpuinfoTestHelper('./test/_cpuinfo_dub_8-4-2')

    def test_drack(self):
        self.__cpuinfoTestHelper('./test/_cpuinfo_drack_4-2-2')

    def test_genosis(self):
        self.__cpuinfoTestHelper('./test/_cpuinfo_genosis_1-1-1')

    def test_rider(self):
        self.__cpuinfoTestHelper('./test/_cpuinfo_rider_4-2-2')

    def test_vrack(self):
        self.__cpuinfoTestHelper('./test/_cpuinfo_vrack_2-1-2')

    def test_8600(self):
        self.__cpuinfoTestHelper('./test/_cpuinfo_hp8600_8-4-2')

    def test_dub(self):
        self.__cpuinfoTestHelper('./test/_cpuinfo_dub_8-4-2')

    def test_srdsvr05(self):
        self.__cpuinfoTestHelper('./test/_cpuinfo_srdsvr05_ht_12-6-2-2')

    def test_srdsvr09(self):
        self.__cpuinfoTestHelper('./test/_cpuinfo_srdsvr09_48-12-4')

    def __cpuinfoTestHelper(self, pathCpuInfo):
        # File format: _cpuinfo_dub_x-x-x where x-x-x is totalCores-coresPerProc-numProcs
        pathCpuInfo = os.path.join(os.path.dirname(__file__), pathCpuInfo)
        renderHost, coreInfo = self.rqd.machine.testInitMachineStats(pathCpuInfo)
        totalCores, coresPerProc, numProcs = pathCpuInfo.split('_')[-1].split('-')[:3]
        assert renderHost.num_procs == int(numProcs), '%s == %s' % (renderHost.numProcs, numProcs)
        assert renderHost.cores_per_proc == int(coresPerProc) * 100, '%s == %s' % (renderHost.coresPerProc, int(coresPerProc) * 100)
        assert coreInfo.total_cores == int(totalCores) * 100, '%s == %s' % (coreInfo.total_cores, int(totalCores) * 100)
        assert coreInfo.idle_cores == int(totalCores) * 100, '%s == %s' % (coreInfo.idle_cores, int(totalCores) * 100)
        assert coreInfo.locked_cores == 0, coreInfo.locked_cores
        assert coreInfo.booked_cores == 0, coreInfo.booked_cores
        if pathCpuInfo.find('_ht_') != -1:
            assert renderHost.attributes['hyperthreadingMultiplier'] ==  pathCpuInfo.split('-')[3]

class TestRqdWithGrpc(SetupCuebotListener):
    def setUp(self):
        #Constants.DISABLE_NIMBY = True
        self.rqd = RqCore()
        self.servicer.last_reportRqdStartup = None
        self.servicer.last_reportStatus = None
        self.servicer.last_reportRunningFrameCompletion = None
        self.rqd.start()

    def tearDown(self):
        self.rqd.shutdownRqdNow()

    def _verifyStatusReport(self, report):
        assert len(report.host.name) > 0
        #nimbyEnabled = False
        assert report.host.num_procs > 0
        assert report.host.cores_per_proc > 0
        assert report.host.total_swap > 0
        assert report.host.total_mem > 0
        assert report.host.total_mcp > 0
        assert report.host.free_swap > 0
        assert report.host.free_mem > 0
        assert report.host.free_mcp > 0
        #load = 6
        assert report.host.boot_time > 0
        assert len(report.host.tags) > 0 
        assert len(report.procs) > 0
    
    def _test_send_startup(self):
        report = self.servicer.last_reportRqdStartup
        self._verifyStatusReport(report)

    def _test_send_status(self):
        self.servicer.last_reportStatus = None
        self.rqd.network.reportStatus(self.rqd.machine.getHostReport())
        report = self.servicer.last_reportStatus
        self._verifyStatusReport(report)
        
if __name__ == '__main__':
    unittest.main()

