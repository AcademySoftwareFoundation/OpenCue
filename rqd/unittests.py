#!/usr/bin/python


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





import unittest

import rqutil

from rqcore import RqCore
from rqnetwork import Network
from rqnetwork import RunningFrame
from rqmachine import Machine
from rqnimby import Nimby

import rqconstants

import time

from test.test_cuebot_listener import RqdReportStatic

#class setup_rqd(unittest.TestCase):

class setup_cuebot_listener(unittest.TestCase):
    listener = RqdReportStatic(rqconstants.STRING_TO_CUEBOT, rqconstants.CUEBOT_PORT)
    listener.verbose = 0

class test_Machine_cpuinfo(unittest.TestCase):
    def setUp(self):
        #rqconstants.DISABLE_NIMBY = True
        self.rqd = RqCore()

    def tearDown(self):
        del self.rqd

    def _printme(self):
        print len(self.rqd.machine.procDict)
        print self.rqd.machine._procCount
        print self.rqd.machine._coreCount
        print self.rqd.machine._coresPerProc

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
        renderHost, coreInfo = self.rqd.machine.testInitMachineStats(pathCpuInfo)
        totalCores, coresPerProc, numProcs = pathCpuInfo.split('_')[-1].split('-')[:3]
        assert renderHost.numProcs == int(numProcs), '%s == %s' % (renderHost.numProcs, numProcs)
        assert renderHost.coresPerProc == int(coresPerProc) * 100, '%s == %s' % (renderHost.coresPerProc, int(coresPerProc) * 100)
        assert coreInfo.totalCores == int(totalCores) * 100, '%s == %s' % (coreInfo.totalCores, int(totalCores) * 100)
        assert coreInfo.idleCores == int(totalCores) * 100, '%s == %s' % (coreInfo.idleCores, int(totalCores) * 100)
        assert coreInfo.lockedCores == 0, coreInfo.lockedCores
        assert coreInfo.bookedCores == 0, coreInfo.bookedCores
        if pathCpuInfo.find('_ht_') != -1:
            assert renderHost.attributes['hyperthreadingMultiplier'] ==  pathCpuInfo.split('-')[3]

class test_rqd_with_ice(setup_cuebot_listener):
    def setUp(self):
        #Constants.DISABLE_NIMBY = True
        self.rqd = RqCore()
        self.listener.last_reportRqdStartup = None
        self.listener.last_reportStatus = None
        self.listener.last_reportRunningFrameCompletion = None
        self.rqd.start()

    def tearDown(self):
        self.rqd.shutdownRqdNow()
        self.rqd.wait()
        del self.rqd
    
    def _verify_status_report(self, report):
        assert len(report.host.name) > 0
        #nimbyEnabled = False
        assert report.host.numProcs > 0
        assert report.host.coresPerProc > 0
        assert report.host.totalSwap > 0
        assert report.host.totalMem > 0
        assert report.host.totalMcp > 0
        assert report.host.freeSwap > 0
        assert report.host.freeMem > 0
        assert report.host.freeMcp > 0
        #load = 6
        assert report.host.bootTime > 0
        assert len(report.host.tags) > 0 
        assert len(report.procs) > 0
    
    def _test_send_startup(self):
        report = self.listener.last_reportRqdStartup
        self._verify_status_report(report)

    def _test_send_status(self):
        self.listener.last_reportStatus = None
        self.rqd.network.reportStatus(self.rqd.machine.getHostReport())
        report = self.listener.last_reportStatus
        self._verify_status_report(report)
        
if __name__ == '__main__':
    unittest.main()

