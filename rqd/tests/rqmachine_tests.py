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

import pyfakefs.fake_filesystem_unittest

# Decorators are applied at import time, so we have to mock Memoize here; it's
# a function that caches results of method calls and makes it difficult to mock
# methods that use it.
mock.patch('rqd.rqutil.Memoize', lambda x: x).start()

import rqd.rqconstants
import rqd.rqcore
import rqd.rqmachine
import rqd.rqnimby
import rqd.compiled_proto.report_pb2


CPUINFO = """processor	: 0
vendor_id	: GenuineIntel
cpu family	: 6
model		: 63
model name	: Intel(R) Xeon(R) CPU E5-2699 v3 @ 2.30GHz
stepping	: 2
microcode	: 0x1
cpu MHz		: 2299.998
cache size	: 46080 KB
physical id	: 0
siblings	: 1
core id		: 0
cpu cores	: 1
apicid		: 0
initial apicid	: 0
fpu		: yes
fpu_exception	: yes
cpuid level	: 13
wp		: yes
flags		: fpu vme de pse tsc msr pae mce cx8 apic sep mtrr pge mca cmov pat pse36 clflush mmx fxsr sse sse2 ss syscall nx pdpe1gb rdtscp lm constant_tsc arch_perfmon rep_good nopl cpuid tsc_known_freq pni pclmulqdq vmx ssse3 fma cx16 pcid sse4_1 sse4_2 x2apic movbe popcnt tsc_deadline_timer aes xsave avx f16c rdrand hypervisor lahf_lm abm invpcid_single pti ibrs ibpb tpr_shadow vnmi flexpriority ept vpid fsgsbase tsc_adjust bmi1 avx2 smep bmi2 erms invpcid xsaveopt arat md_clear
bugs		: cpu_meltdown spectre_v1 spectre_v2 spec_store_bypass l1tf mds
bogomips	: 4599.99
clflush size	: 64
cache_alignment	: 64
address sizes	: 40 bits physical, 48 bits virtual
power management:

processor	: 1
vendor_id	: GenuineIntel
cpu family	: 6
model		: 63
model name	: Intel(R) Xeon(R) CPU E5-2699 v3 @ 2.30GHz
stepping	: 2
microcode	: 0x1
cpu MHz		: 2299.998
cache size	: 46080 KB
physical id	: 1
siblings	: 1
core id		: 0
cpu cores	: 1
apicid		: 1
initial apicid	: 1
fpu		: yes
fpu_exception	: yes
cpuid level	: 13
wp		: yes
flags		: fpu vme de pse tsc msr pae mce cx8 apic sep mtrr pge mca cmov pat pse36 clflush mmx fxsr sse sse2 ss syscall nx pdpe1gb rdtscp lm constant_tsc arch_perfmon rep_good nopl cpuid tsc_known_freq pni pclmulqdq vmx ssse3 fma cx16 pcid sse4_1 sse4_2 x2apic movbe popcnt tsc_deadline_timer aes xsave avx f16c rdrand hypervisor lahf_lm abm invpcid_single pti ibrs ibpb tpr_shadow vnmi flexpriority ept vpid fsgsbase tsc_adjust bmi1 avx2 smep bmi2 erms invpcid xsaveopt arat md_clear
bugs		: cpu_meltdown spectre_v1 spectre_v2 spec_store_bypass l1tf mds
bogomips	: 4599.99
clflush size	: 64
cache_alignment	: 64
address sizes	: 40 bits physical, 48 bits virtual
power management:

"""


MEMINFO_MODERATE_USAGE = """MemTotal:       32942144 kB
MemFree:         5339060 kB
Cached:         20360116 kB
SwapFree:        4105212 kB
"""

MEMINFO_NONE_FREE = """MemTotal:       32942144 kB
MemFree:               0 kB
Cached:                0 kB
SwapFree:        4105212 kB
"""

MEMINFO_NO_SWAP = """MemTotal:       32942144 kB
MemFree:         5339060 kB
Cached:         20360116 kB
SwapFree:              0 kB
"""


LOADAVG_LOW_USAGE = '0.25 0.16 0.11 2/1655 50733'

LOADAVG_HIGH_USAGE = '10.38 10.12 10.22 2/1655 50733'


INITTAB_DESKTOP = '''rc::bootwait:/etc/rc
id:5:initdefault:
1:1:respawn:/etc/getty 9600 tty1
2:1:respawn:/etc/getty 9600 tty2
3:1:respawn:/etc/getty 9600 tty3
4:1:respawn:/etc/getty 9600 tty4
'''

INITTAB_SERVER = '''rc::bootwait:/etc/rc
id:3:initdefault:
1:1:respawn:/etc/getty 9600 tty1
2:1:respawn:/etc/getty 9600 tty2
3:1:respawn:/etc/getty 9600 tty3
4:1:respawn:/etc/getty 9600 tty4
'''


@mock.patch('platform.system', new=mock.MagicMock(return_value='Linux'))
@mock.patch('os.statvfs', new=mock.MagicMock())
@mock.patch.object(rqd.rqmachine.Machine, 'getBootTime', new=mock.MagicMock(return_value=9876))
@mock.patch('rqd.rqutil.getHostname', new=mock.MagicMock(return_value='arbitrary-hostname'))
class MachineTests(pyfakefs.fake_filesystem_unittest.TestCase):
    def setUp(self):
        self.setUpPyfakefs()
        self.fs.create_file('/proc/cpuinfo', contents=CPUINFO)
        self.loadavg = self.fs.create_file('/proc/loadavg', contents=LOADAVG_LOW_USAGE)

        self.rqCore = mock.MagicMock(spec=rqd.rqcore.RqCore)
        self.nimby = mock.MagicMock(spec=rqd.rqnimby.Nimby)
        self.rqCore.nimby = self.nimby
        self.nimby.active = False
        self.nimby.locked = False
        self.coreDetail = rqd.compiled_proto.report_pb2.CoreDetail(total_cores=2)

        self.machine = rqd.rqmachine.Machine(self.rqCore, self.coreDetail)

    @mock.patch('platform.system', new=mock.MagicMock(return_value='Linux'))
    def test_isNimbySafeToRunJobs(self):
        self.fs.create_file('/proc/meminfo', contents=MEMINFO_MODERATE_USAGE)

        self.assertTrue(self.machine.isNimbySafeToRunJobs())

    @mock.patch('platform.system', new=mock.MagicMock(return_value='Linux'))
    def test_isNimbySafeToRunJobs_noFreeMem(self):
        self.fs.create_file('/proc/meminfo', contents=MEMINFO_NONE_FREE)

        self.assertFalse(self.machine.isNimbySafeToRunJobs())

    @mock.patch('platform.system', new=mock.MagicMock(return_value='Linux'))
    def test_isNimbySafeToRunJobs_noFreeSwap(self):
        self.fs.create_file('/proc/meminfo', contents=MEMINFO_NO_SWAP)

        self.assertFalse(self.machine.isNimbySafeToRunJobs())

    @mock.patch.object(
        rqd.rqmachine.Machine, 'isNimbySafeToRunJobs', new=mock.MagicMock(return_value=True))
    def test_isNimbySafeToUnlock(self):
        self.loadavg.set_contents(LOADAVG_LOW_USAGE)
        rqd.rqconstants.MAXIMUM_LOAD = 5

        self.assertTrue(self.machine.isNimbySafeToUnlock())

    @mock.patch.object(
        rqd.rqmachine.Machine, 'isNimbySafeToRunJobs', new=mock.MagicMock(return_value=False))
    def test_isNimbySafeToUnlock_unsafeToRunJobs(self):
        self.assertFalse(self.machine.isNimbySafeToUnlock())

    @mock.patch.object(
        rqd.rqmachine.Machine, 'isNimbySafeToRunJobs', new=mock.MagicMock(return_value=True))
    def test_isNimbySafeToUnlock_loadTooHigh(self):
        self.loadavg.set_contents(LOADAVG_HIGH_USAGE)
        rqd.rqconstants.MAXIMUM_LOAD = 5

        self.assertFalse(self.machine.isNimbySafeToUnlock())

    def test_isDesktop_inittabDesktop(self):
        rqd.rqconstants.OVERRIDE_IS_DESKTOP = False
        self.fs.create_file(rqd.rqconstants.PATH_INITTAB, contents=INITTAB_DESKTOP)

        self.assertTrue(self.machine.isDesktop())

    def test_isDesktop_inittabServer(self):
        rqd.rqconstants.OVERRIDE_IS_DESKTOP = False
        self.fs.create_file(rqd.rqconstants.PATH_INITTAB, contents=INITTAB_SERVER)

        self.assertFalse(self.machine.isDesktop())

    def test_isDesktop_initTarget(self):
        rqd.rqconstants.OVERRIDE_IS_DESKTOP = False
        self.fs.create_file(rqd.rqconstants.PATH_INITTAB)
        symlink_target = '/lib/systemd/system/graphical.target'
        self.fs.create_file(symlink_target)
        self.fs.create_symlink(rqd.rqconstants.PATH_INIT_TARGET, symlink_target)

        self.assertTrue(self.machine.isDesktop())

    def test_isDesktop_override(self):
        rqd.rqconstants.OVERRIDE_IS_DESKTOP = True

        self.assertTrue(self.machine.isDesktop())

    def test_isUserLoggedIn(self):
        # create file /tmp/.X11-unix/X20
        # mock /usr/bin/who to return
        # <username> :20           2017-11-07 18:21 (:20)

        # other case, mock psutil to return gnome-session as running

        self.machine.isUserLoggedIn()


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
