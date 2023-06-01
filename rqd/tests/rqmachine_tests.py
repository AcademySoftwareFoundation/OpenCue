#!/usr/bin/env python
#  Copyright Contributors to the OpenCue Project
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


"""Tests for rqd.rqmachine."""


from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import os
import unittest

import mock
import pyfakefs.fake_filesystem_unittest

import rqd.rqconstants
import rqd.rqcore
import rqd.rqmachine
import rqd.rqnetwork
import rqd.rqnimby
import rqd.rqutil
import rqd.compiled_proto.host_pb2
import rqd.compiled_proto.report_pb2
import rqd.compiled_proto.rqd_pb2


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

LOADAVG_HIGH_USAGE = '20.38 20.12 20.22 2/1655 50733'

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

PROC_STAT = '''cpu  116544 0 86685 104701644 11860 0 3755 0 0 0
cpu0 17957 0 12259 17453918 1175 0 1777 0 0 0
cpu1 21940 0 16589 17425773 2560 0 476 0 0 0
cpu2 18385 0 14660 17459681 2924 0 435 0 0 0
cpu3 18664 0 14591 17456724 1604 0 336 0 0 0
cpu4 18138 0 14408 17450097 1984 0 402 0 0 0
cpu5 21460 0 14178 17455448 1610 0 329 0 0 0
intr 39473717 33 0 0 16 277 0 0 0 1 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1227 399900 2792 48 2685 0 1000486 1 0 1202082 2007718 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
ctxt 76857443
btime 1569882758
processes 19948
procs_running 1
procs_blocked 0
softirq 10802040 0 3958368 410 1972314 394501 0 1 3631586 0 844860
'''

PROC_STAT_SUFFIX = (' S 7 105 105 0 -1 4210688 317 0 1 0 31 13 0 0 20 0 1 0 17385159 '
                   '4460544 154 18446744073709551615 4194304 4204692 140725890735264 0 0 0 0 '
                   '16781318 0 0 0 0 17 4 0 0 0 0 0 6303248 6304296 23932928 140725890743234 '
                   '140725890743420 140725890743420 140725890744298 0')
PROC_PID_STAT = '105 (time)' + PROC_STAT_SUFFIX
PROC_PID_STAT_WITH_SPACES = '105 (test space)' + PROC_STAT_SUFFIX
PROC_PID_STAT_WITH_BRACKETS = '105 (test) (brackets)' + PROC_STAT_SUFFIX

PROC_PID_STATM = '152510 14585 7032 9343 0 65453 0'

PROC_PID_CMDLINE = ' sleep 20'

@mock.patch.object(rqd.rqutil.Memoize, 'isCached', new=mock.MagicMock(return_value=False))
@mock.patch('platform.system', new=mock.MagicMock(return_value='Linux'))
@mock.patch('os.statvfs', new=mock.MagicMock())
@mock.patch('rqd.rqutil.getHostname', new=mock.MagicMock(return_value='arbitrary-hostname'))
class MachineTests(pyfakefs.fake_filesystem_unittest.TestCase):

    @mock.patch('os.statvfs', new=mock.MagicMock())
    @mock.patch('platform.system', new=mock.MagicMock(return_value='Linux'))
    def setUp(self):
        self.setUpPyfakefs()
        self.fs.create_file('/proc/cpuinfo', contents=CPUINFO)
        self.loadavg = self.fs.create_file('/proc/loadavg', contents=LOADAVG_LOW_USAGE)
        self.procStat = self.fs.create_file('/proc/stat', contents=PROC_STAT)
        self.meminfo = self.fs.create_file('/proc/meminfo', contents=MEMINFO_MODERATE_USAGE)

        self.rqCore = mock.MagicMock(spec=rqd.rqcore.RqCore)
        self.nimby = mock.MagicMock(spec=rqd.rqnimby.NimbySelect)
        self.rqCore.nimby = self.nimby
        self.nimby.active = False
        self.nimby.locked = False
        self.coreDetail = rqd.compiled_proto.report_pb2.CoreDetail(total_cores=2)

        self.machine = rqd.rqmachine.Machine(self.rqCore, self.coreDetail)

    @mock.patch('platform.system', new=mock.MagicMock(return_value='Linux'))
    def test_isNimbySafeToRunJobs(self):
        self.meminfo.set_contents(MEMINFO_MODERATE_USAGE)

        self.assertTrue(self.machine.isNimbySafeToRunJobs())

    @mock.patch('platform.system', new=mock.MagicMock(return_value='Linux'))
    def test_isNimbySafeToRunJobs_noFreeMem(self):
        self.meminfo.set_contents(MEMINFO_NONE_FREE)

        self.assertFalse(self.machine.isNimbySafeToRunJobs())

    @mock.patch('platform.system', new=mock.MagicMock(return_value='Linux'))
    def test_isNimbySafeToRunJobs_noFreeSwap(self):
        self.meminfo.set_contents(MEMINFO_NO_SWAP)

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

    @mock.patch('subprocess.check_output')
    def test_isUserLoggedInWithDisplay(self, checkOutputMock):
        displayNum = 20
        self.fs.create_file('/tmp/.X11-unix/X%d' % displayNum)

        def checkOutputReturn(cmd):
            if cmd == ['/usr/bin/who']:
                return '<username> :%d           2017-11-07 18:21 (:%d)\n' % (
                    displayNum, displayNum)
            raise ValueError('unexpected cmd %s' % cmd)

        checkOutputMock.side_effect = checkOutputReturn

        self.assertTrue(self.machine.isUserLoggedIn())

    @mock.patch('psutil.process_iter')
    def test_isUserLoggedInWithRunningProcess(self, processIterMock):
        gnomeProcess = mock.MagicMock()
        gnomeProcess.name.return_value = 'gnome-session'
        processIterMock.return_value = [gnomeProcess]

        self.assertTrue(self.machine.isUserLoggedIn())

    @mock.patch('psutil.process_iter')
    def test_isUserLoggedInWithNoDisplayOrProcess(self, processIterMock):
        gnomeProcess = mock.MagicMock()
        gnomeProcess.name.return_value = 'some-random-process'
        processIterMock.return_value = [gnomeProcess]

        self.assertFalse(self.machine.isUserLoggedIn())

    def _test_rssUpdate(self, proc_stat):
        rqd.rqconstants.SYS_HERTZ = 100
        pid = 105
        frameId = 'unused-frame-id'
        self.fs.create_file('/proc/%d/stat' % pid, contents=proc_stat)
        self.fs.create_file('/proc/%s/cmdline'  % pid, contents=PROC_PID_CMDLINE)
        self.fs.create_file('/proc/%s/statm'  % pid, contents=PROC_PID_STATM)
        runningFrame = rqd.rqnetwork.RunningFrame(self.rqCore,
                                                  rqd.compiled_proto.rqd_pb2.RunFrame())
        runningFrame.pid = pid
        frameCache = {frameId: runningFrame}

        self.machine.rssUpdate(frameCache)

        updatedFrameInfo = frameCache[frameId].runningFrameInfo()
        # pylint: disable=no-member
        self.assertEqual(616, updatedFrameInfo.max_rss)
        self.assertEqual(616, updatedFrameInfo.rss)
        self.assertEqual(4356, updatedFrameInfo.max_vsize)
        self.assertEqual(4356, updatedFrameInfo.vsize)
        self.assertAlmostEqual(0.034444696691, float(updatedFrameInfo.attributes['pcpu']))

    @mock.patch('time.time', new=mock.MagicMock(return_value=1570057887.61))
    def test_rssUpdate(self):
        self._test_rssUpdate(PROC_PID_STAT)

    @mock.patch('time.time', new=mock.MagicMock(return_value=1570057887.61))
    def test_rssUpdateWithSpaces(self):
        self._test_rssUpdate(PROC_PID_STAT_WITH_SPACES)

    @mock.patch('time.time', new=mock.MagicMock(return_value=1570057887.61))
    def test_rssUpdateWithBrackets(self):
        self._test_rssUpdate(PROC_PID_STAT_WITH_BRACKETS)

    @mock.patch.object(
        rqd.rqmachine.Machine, '_Machine__enabledHT', new=mock.MagicMock(return_value=False))
    def test_getLoadAvg(self):
        self.loadavg.set_contents(LOADAVG_HIGH_USAGE)

        self.assertEqual(2038, self.machine.getLoadAvg())

    @mock.patch.object(
        rqd.rqmachine.Machine, '_Machine__enabledHT', new=mock.MagicMock(return_value=True))
    @mock.patch.object(
        rqd.rqmachine.Machine, '_Machine__getHyperthreadingMultiplier',
        new=mock.MagicMock(return_value=2))
    def test_getLoadAvgHT(self):
        self.loadavg.set_contents(LOADAVG_HIGH_USAGE)

        self.assertEqual(1019, self.machine.getLoadAvg())

    def test_getBootTime(self):
        self.procStat.set_contents(PROC_STAT)

        self.assertEqual(1569882758, self.machine.getBootTime())

    def _resetGpuStat(self):
        if hasattr(self.machine, 'gpuNotSupported'):
            delattr(self.machine, 'gpuNotSupported')
        if hasattr(self.machine, 'gpuResults'):
            delattr(self.machine, 'gpuResults')

    @mock.patch.object(
        rqd.rqconstants, 'ALLOW_GPU', new=mock.MagicMock(return_value=True))
    @mock.patch('subprocess.getoutput',
        new=mock.MagicMock(return_value='16130 MiB, 16119 MiB, 1'))
    def test_getGpuStat(self):
        self._resetGpuStat()
        self.assertEqual(1, self.machine.getGpuCount())
        self.assertEqual(16913531, self.machine.getGpuMemoryTotal())
        self.assertEqual(16901997, self.machine.getGpuMemoryFree())

    @mock.patch.object(
        rqd.rqconstants, 'ALLOW_GPU', new=mock.MagicMock(return_value=True))
    @mock.patch('subprocess.getoutput',
        new=mock.MagicMock(return_value="""\
16130 MiB, 16103 MiB, 8
16130 MiB, 16119 MiB, 8
16130 MiB, 16119 MiB, 8
16130 MiB, 16119 MiB, 8
16130 MiB, 4200 MiB, 8
16130 MiB, 16119 MiB, 8
16130 MiB, 16119 MiB, 8
16130 MiB, 16119 MiB, 8"""))
    def test_multipleGpus(self):
        self._resetGpuStat()
        self.assertEqual(8, self.machine.getGpuCount())
        self.assertEqual(135308248, self.machine.getGpuMemoryTotal())
        self.assertEqual(122701222, self.machine.getGpuMemoryFree())

    def test_getPathEnv(self):
        rqd.rqconstants.RQD_USE_PATH_ENV_VAR = False
        self.assertEqual(
            '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin',
            self.machine.getPathEnv())

    @mock.patch('tempfile.gettempdir')
    def test_getTempPath(self, gettempdirMock):
        tmpDir = '/some/random/tmpdir'
        gettempdirMock.return_value = tmpDir

        self.assertEqual('%s/' % tmpDir, self.machine.getTempPath())

    def test_getTempPathMcp(self):
        self.fs.create_dir('/mcp')

        self.assertEqual('/mcp/', self.machine.getTempPath())

    @mock.patch('subprocess.Popen', autospec=True)
    def test_reboot(self, popenMock):
        self.machine.reboot()

        popenMock.assert_called_with(['/usr/bin/sudo', '/sbin/reboot', '-f'])

    def test_getHostInfo(self):
        # pylint: disable=no-member
        hostInfo = self.machine.getHostInfo()

        self.assertEqual(4105212, hostInfo.free_swap)
        self.assertEqual(25699176, hostInfo.free_mem)
        self.assertEqual('0', hostInfo.attributes['swapout'])
        self.assertEqual(25, hostInfo.load)
        self.assertEqual(False, hostInfo.nimby_enabled)
        self.assertEqual(False, hostInfo.nimby_locked)
        self.assertEqual(rqd.compiled_proto.host_pb2.UP, hostInfo.state)

    def test_getHostReport(self):
        frame1 = mock.MagicMock(spec=rqd.rqnetwork.RunningFrame)
        frame1Info = rqd.compiled_proto.report_pb2.RunningFrameInfo(resource_id='arbitrary-id-1')
        frame1.runningFrameInfo.return_value = frame1Info
        frame2 = mock.MagicMock(spec=rqd.rqnetwork.RunningFrame)
        frame2Info = rqd.compiled_proto.report_pb2.RunningFrameInfo(resource_id='arbitrary-id-2')
        frame2.runningFrameInfo.return_value = frame2Info
        frameIds = ['frame1', 'frame2']
        frames = {
            frameIds[0]: frame1,
            frameIds[1]: frame2,
        }
        self.rqCore.getFrameKeys.return_value = frameIds
        self.rqCore.getFrame.side_effect = lambda frameId: frames[frameId]
        coreDetail = rqd.compiled_proto.report_pb2.CoreDetail(
            total_cores=152, idle_cores=57, locked_cores=30, booked_cores=65)
        self.rqCore.getCoreInfo.return_value = coreDetail

        hostReport = self.machine.getHostReport()

        # pylint: disable=no-member

        # Verify host info was copied into the report.
        self.assertEqual(4105212, hostReport.host.free_swap)
        self.assertEqual(25699176, hostReport.host.free_mem)
        # Verify frames were copied into the report.
        self.assertEqual(frame1Info, hostReport.frames[0])
        self.assertEqual(frame2Info, hostReport.frames[1])
        # Verify core info was copied into the report.
        self.assertEqual(coreDetail, hostReport.core_info)

    def test_getBootReport(self):
        bootReport = self.machine.getBootReport()

        # pylint: disable=no-member

        # Verify host info was copied into the report.
        self.assertEqual(4105212, bootReport.host.free_swap)
        self.assertEqual(25699176, bootReport.host.free_mem)

    def test_reserveHT(self):
        """
        Total 2 physical(ph) processors with 4 cores each with 2 threads each (total 16 threads)
        note: reserving odd threads will result in even threads when there is no mono-thread cores
        step1 - taskset0: Reserve 4 threads (2 cores) (ph0->0,1)
        step2 - taskset1: Reserve 6 threads (3 cores) (ph1->0,1,2)
        step3 - Release cores on taskset0 (ph0->0,1)
        step4 - taskset3: Reserve 6 threads (3 cores) (ph0->0,1,2)
        step5 - taskset4: 4 remaining, Reserve 4 threads (2 cores) (ph0->3 + ph1->3)
        step6 - taskset5: No more cores
        """
        cpuInfo = os.path.join(os.path.dirname(__file__), 'cpuinfo', '_cpuinfo_shark_ht_8-4-2-2')
        self.fs.add_real_file(cpuInfo)
        self.machine.testInitMachineStats(cpuInfo)

        self.machine.setupTaskset()

        # ------------------------step1-------------------------
        # phys_id 0
        #   - core_id 0
        #     - process_id 0
        #     - process_id 8
        #   - core_id 1
        #     - process_id 1
        #     - process_id 9
        tasksets0 = self.machine.reserveHT(400)
        # pylint: disable=no-member
        self.assertCountEqual(['0', '8', '1', '9'],
                              sorted(tasksets0.split(',')))

        # ------------------------step2-------------------------
        # phys_id 1
        #   - core_id 0
        #     - process_id 4
        #     - process_id 12
        #   - core_id 1
        #     - process_id 5
        #     - process_id 13
        #   - core_id 2
        #     - process_id 6
        #     - process_id 14
        tasksets1 = self.machine.reserveHT(600)
        # pylint: disable=no-member
        self.assertCountEqual(['4', '12', '5', '13', '6', '14'],
                              sorted(tasksets1.split(',')))

        # reserved cores got updated properly
        # pylint: disable=no-member
        self.assertCountEqual([0, 1], self.coreDetail.reserved_cores[0].coreid)

        # Make sure tastsets don't overlap
        self.assertTrue(set(tasksets0.split(',')).isdisjoint(tasksets1.split(',')))

        # ------------------------step3-------------------------
        # Releasing a physcore shouldn't impact other physcores
        self.machine.releaseHT(tasksets0)
        # pylint: disable=no-member
        self.assertTrue(1 in self.coreDetail.reserved_cores)
        # pylint: disable=no-member
        self.assertCountEqual([0, 1, 2], self.coreDetail.reserved_cores[1].coreid)

        # ------------------------step4-------------------------
        # phys_id 0
        #   - core_id 0
        #     - process_id 0
        #     - process_id 8
        #   - core_id 1
        #     - process_id 1
        #     - process_id 9
        #   - core_id 2
        #     - process_id 2
        #     - process_id 10
        tasksets3 = self.machine.reserveHT(600)
        # pylint: disable=no-member
        self.assertCountEqual(['0', '8', '1', '9', '2', '10'], sorted(tasksets3.split(',')))

        # ------------------------step5-------------------------
        # phys_id 0
        #   - core_id 3
        #     - process_id 3
        #     - process_id 11
        # phys_id 1
        #   - core_id 3
        #     - process_id 7
        #     - process_id 15
        tasksets4 = self.machine.reserveHT(400)
        # pylint: disable=no-member
        self.assertCountEqual(['3', '11', '7', '15'], sorted(tasksets4.split(',')))

        # ------------------------step6-------------------------
        # No cores available
        with self.assertRaises(rqd.rqexceptions.CoreReservationFailureException):
            self.machine.reserveHT(200)

    def test_reserveHybridHT(self):
        """
        Total 1 physical(ph) processors with 8 P-cores(2 threads) and 8 E-cores(1 thread), total 24 threads.
        note: reserving odd threads will result in even threads when there is no mono-thread cores,
        which is not the case here. it should reserve E-cores to match the odd request.
        step1 - taskset0: Reserve 4 threads (2P), 4 threads occupied
        step2 - taskset1: Reserve 5 threads (2P, 1E), 9 threads occupied
        step3 - taskset2: Reserve 6 threads (3P), 15 threads occupied
        step4 - Release taskset0, 3P and 7E remaining, 11 threads occupied
        step5 - taskset3: Reserve 12 threads (3P, 6E), 23 threads occupied
        step6 - taskset4: Reserve 1 thread (1E), 24 threads occupied
        step7 - Reserve 1 thread (1E), no more free cores
        """
        cpuInfo = os.path.join(os.path.dirname(__file__), 'cpuinfo', '_cpuinfo_i9_12900_hybrid_ht_24-24-1-1')
        self.fs.add_real_file(cpuInfo)
        self.machine.testInitMachineStats(cpuInfo)

        self.machine.setupTaskset()

        # ------------------------step1-------------------------
        # phys_id 0
        #   - P core_id 0
        #     - process_id 0
        #     - process_id 1
        #   - P core_id 4
        #     - process_id 2
        #     - process_id 3
        #   - P core_id 8
        #     - process_id 4
        #     - process_id 5
        #   - P core_id 12
        #     - process_id 6
        #     - process_id 7
        #   - P core_id 16
        #     - process_id 8
        #     - process_id 9
        #   - P core_id 20
        #     - process_id 10
        #     - process_id 11
        #   - P core_id 24
        #     - process_id 12
        #     - process_id 13
        #   - P core_id 28
        #     - process_id 14
        #     - process_id 15

        #   - E core_id 32
        #     - process_id 16
        #   - E core_id 33
        #     - process_id 17
        #   - E core_id 34
        #     - process_id 18
        #   - E core_id 35
        #     - process_id 19
        #   - E core_id 36
        #     - process_id 20
        #   - E core_id 37
        #     - process_id 21
        #   - E core_id 38
        #     - process_id 22
        #   - E core_id 39
        #     - process_id 23
        tasksets0 = self.machine.reserveHT(400)

        # should reserve 2P (0,1, 2,3)
        # pylint: disable=no-member
        self.assertCountEqual(['0', '1', '2', '3'], tasksets0.split(','))

        # should have 2 cores occupied
        # pylint: disable=no-member
        self.assertCountEqual([0, 4], self.coreDetail.reserved_cores[0].coreid)
        # should have 4 threads occupied
        self.assertEqual(len(tasksets0.split(',')), 4)


        # ------------------------step2-------------------------
        tasksets1 = self.machine.reserveHT(500)

        # should reserve 2P + 1E (4,5, 6,7, 16)
        # pylint: disable=no-member
        self.assertCountEqual(['4', '5', '6', '7', '16'], tasksets1.split(','))

        # should have 5 cores occupied
        # pylint: disable=no-member
        self.assertCountEqual([0, 4, 8, 12, 32], self.coreDetail.reserved_cores[0].coreid)
        # should have 9 threads occupied
        self.assertEqual(len(tasksets0.split(','))
                         + len(tasksets1.split(',')),
                         9)


        # ------------------------step3-------------------------
        tasksets2 = self.machine.reserveHT(600)

        # should reserve 3P (8,9, 10,11, 12,13)
        # pylint: disable=no-member
        self.assertCountEqual(['8', '9', '10', '11', '12', '13'], tasksets2.split(','))

        # should have 8 cores occupied
        # pylint: disable=no-member
        self.assertCountEqual([0, 4, 8, 12, 16, 20, 24, 32], self.coreDetail.reserved_cores[0].coreid)
        # should have 15 threads occupied
        self.assertEqual(len(tasksets0.split(','))
                         + len(tasksets1.split(','))
                         + len(tasksets2.split(',')),
                         15)


        # ------------------------step4-------------------------
        self.machine.releaseHT(tasksets0)
        # should release 2P (0,1, 2,3)
        # should have 6 cores occupied
        # pylint: disable=no-member
        self.assertCountEqual([8, 12, 16, 20, 24, 32], self.coreDetail.reserved_cores[0].coreid)
        # should have 11 threads occupied
        self.assertEqual(len(tasksets1.split(','))
                         + len(tasksets2.split(',')),
                         11)


        # ------------------------step5-------------------------
        tasksets3 = self.machine.reserveHT(1200)

        # should reserve 3P + 6E (0,1, 2,3, 14,15, 17, 18, 19, 20, 21, 22)
        # pylint: disable=no-member
        self.assertCountEqual(['0', '1', '2', '3', '14', '15', '17', '18', '19', '20', '21', '22'], tasksets3.split(','))

        # should have 15 cores occupied, 1E free
        # pylint: disable=no-member
        self.assertCountEqual([0, 4, 8, 12, 16, 20, 24, 28, 32, 33, 34, 35, 36, 37, 38],
                              self.coreDetail.reserved_cores[0].coreid)

        # should have 23 threads occupied
        self.assertEqual(len(tasksets1.split(','))
                         + len(tasksets2.split(','))
                         + len(tasksets3.split(',')),
                         23)

        # ------------------------step6-------------------------
        tasksets4 = self.machine.reserveHT(100)

        # should reserve 1E (23)
        # pylint: disable=no-member
        self.assertCountEqual(['23'], tasksets4.split(','))

        # Make sure 24 threads are occupied
        self.assertEqual(len(tasksets1.split(','))
                         + len(tasksets2.split(','))
                         + len(tasksets3.split(','))
                         + len(tasksets4.split(',')),
                         24)

        # ------------------------step7-------------------------
        # No cores available
        with self.assertRaises(rqd.rqexceptions.CoreReservationFailureException):
            self.machine.reserveHT(100)


    def test_tags(self):
        tags = ["test1", "test2", "test3"]
        rqd.rqconstants.RQD_TAGS = " ".join(tags)

        machine = rqd.rqmachine.Machine(self.rqCore, self.coreDetail)

        self.assertTrue(all(tag in machine.__dict__['_Machine__renderHost'].tags for tag in tags))


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

    def test_srdsvr05(self):
        self.__cpuinfoTestHelper('_cpuinfo_srdsvr05_ht_12-6-2-2')

    def test_srdsvr09(self):
        self.__cpuinfoTestHelper('_cpuinfo_srdsvr09_48-12-4')

    def test_i9_12900(self):
        self.__cpuinfoTestHelper('_cpuinfo_i9_12900_hybrid_ht_24-24-1-1')

    def __cpuinfoTestHelper(self, pathCpuInfo):
        # File format: _cpuinfo_dub_x-x-x where x-x-x is totalCores-coresPerProc-numProcs
        pathCpuInfo = os.path.join(os.path.dirname(__file__), 'cpuinfo', pathCpuInfo)
        renderHost, coreInfo = self.rqd.machine.testInitMachineStats(pathCpuInfo)
        totalCores, coresPerProc, numProcs = pathCpuInfo.split('_')[-1].split('-')[:3]

        # pylint: disable=no-member
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
