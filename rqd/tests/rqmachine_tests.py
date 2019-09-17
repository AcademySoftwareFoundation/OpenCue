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

processor	: 2
vendor_id	: GenuineIntel
cpu family	: 6
model		: 63
model name	: Intel(R) Xeon(R) CPU E5-2699 v3 @ 2.30GHz
stepping	: 2
microcode	: 0x1
cpu MHz		: 2299.998
cache size	: 46080 KB
physical id	: 2
siblings	: 1
core id		: 0
cpu cores	: 1
apicid		: 2
initial apicid	: 2
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

processor	: 3
vendor_id	: GenuineIntel
cpu family	: 6
model		: 63
model name	: Intel(R) Xeon(R) CPU E5-2699 v3 @ 2.30GHz
stepping	: 2
microcode	: 0x1
cpu MHz		: 2299.998
cache size	: 46080 KB
physical id	: 3
siblings	: 1
core id		: 0
cpu cores	: 1
apicid		: 3
initial apicid	: 3
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

processor	: 4
vendor_id	: GenuineIntel
cpu family	: 6
model		: 63
model name	: Intel(R) Xeon(R) CPU E5-2699 v3 @ 2.30GHz
stepping	: 2
microcode	: 0x1
cpu MHz		: 2299.998
cache size	: 46080 KB
physical id	: 4
siblings	: 1
core id		: 0
cpu cores	: 1
apicid		: 4
initial apicid	: 4
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

processor	: 5
vendor_id	: GenuineIntel
cpu family	: 6
model		: 63
model name	: Intel(R) Xeon(R) CPU E5-2699 v3 @ 2.30GHz
stepping	: 2
microcode	: 0x1
cpu MHz		: 2299.998
cache size	: 46080 KB
physical id	: 5
siblings	: 1
core id		: 0
cpu cores	: 1
apicid		: 5
initial apicid	: 5
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


MEMINFO = """MemTotal:       32942144 kB
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


@mock.patch('os.statvfs', new=mock.MagicMock())
@mock.patch.object(rqd.rqmachine.Machine, 'getBootTime', new=mock.MagicMock(return_value=9876))
@mock.patch('rqd.rqutil.getHostname', new=mock.MagicMock(return_value='arbitrary-hostname'))
class MachineTests(pyfakefs.fake_filesystem_unittest.TestCase):
    def setUp(self):
        self.setUpPyfakefs()
        self.fs.create_file('/proc/cpuinfo', contents=CPUINFO)
        #self.fs.create_file('/proc/meminfo', contents=MEMINFO)
        self.fs.create_file('/proc/loadavg', contents='0.25 0.16 0.11 2/1655 50733')

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

    @mock.patch('platform.system', new=mock.MagicMock(return_value='Linux'))
    def test_isNimbySafeToRunJobs(self):
        rqCore = mock.MagicMock(spec=rqd.rqcore.RqCore)
        rqCore.nimby = mock.MagicMock(spec=rqd.rqnimby.Nimby)
        rqCore.nimby.active = True
        rqCore.nimby.locked = True
        coreDetail = rqd.compiled_proto.report_pb2.CoreDetail()
        self.fs.create_file('/proc/meminfo', contents=MEMINFO)
        machine = rqd.rqmachine.Machine(rqCore, coreDetail)

        self.assertTrue(machine.isNimbySafeToRunJobs())

    @mock.patch('platform.system', new=mock.MagicMock(return_value='Linux'))
    def test_isNimbySafeToRunJobs_noFreeMem(self):
        rqCore = mock.MagicMock(spec=rqd.rqcore.RqCore)
        rqCore.nimby = mock.MagicMock(spec=rqd.rqnimby.Nimby)
        rqCore.nimby.active = True
        rqCore.nimby.locked = True
        coreDetail = rqd.compiled_proto.report_pb2.CoreDetail()
        self.fs.create_file('/proc/meminfo', contents=MEMINFO_NONE_FREE)
        machine = rqd.rqmachine.Machine(rqCore, coreDetail)

        self.assertFalse(machine.isNimbySafeToRunJobs())

    @mock.patch('platform.system', new=mock.MagicMock(return_value='Linux'))
    def test_isNimbySafeToRunJobs_noFreeSwap(self):
        rqCore = mock.MagicMock(spec=rqd.rqcore.RqCore)
        rqCore.nimby = mock.MagicMock(spec=rqd.rqnimby.Nimby)
        rqCore.nimby.active = True
        rqCore.nimby.locked = True
        coreDetail = rqd.compiled_proto.report_pb2.CoreDetail()
        self.fs.create_file('/proc/meminfo', contents=MEMINFO_NO_SWAP)
        machine = rqd.rqmachine.Machine(rqCore, coreDetail)

        self.assertFalse(machine.isNimbySafeToRunJobs())


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
