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
        self.nimby = mock.MagicMock(spec=rqd.rqnimby.Nimby)
        self.rqCore.nimby = self.nimby
        self.nimby.is_ready = False
        self.nimby.locked = False
        self.nimby._Nimby__on_interaction.return_value = None
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
    @mock.patch('psutil.Process')
    def test_rssUpdate(self, processMock):
        processMock.return_value.cmdline.return_value = "some_command"
        self._test_rssUpdate(PROC_PID_STAT)

    @mock.patch('time.time', new=mock.MagicMock(return_value=1570057887.61))
    @mock.patch('psutil.Process')
    def test_rssUpdateWithSpaces(self, processMock):
        self._test_rssUpdate(PROC_PID_STAT_WITH_SPACES)

    @mock.patch('time.time', new=mock.MagicMock(return_value=1570057887.61))
    @mock.patch('psutil.Process')
    def test_rssUpdateWithBrackets(self, processMock):
        self._test_rssUpdate(PROC_PID_STAT_WITH_BRACKETS)

    @mock.patch.object(
        rqd.rqmachine.Machine, '_Machine__enabledHT', new=mock.MagicMock(return_value=False))
    def test_getLoadAvg(self):
        self.loadavg.set_contents(LOADAVG_HIGH_USAGE)

        self.assertEqual(2038, self.machine.getLoadAvg())

    @mock.patch.object(
        rqd.rqmachine.Machine, '_Machine__enabledHT', new=mock.MagicMock(return_value=True))
    @mock.patch.object(
        rqd.rqmachine.Machine, 'getHyperthreadingMultiplier',
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
        Total 2 physical(ph) processors with 4 cores each with 2 threads each
        step1 - taskset1: Reserve 3 cores (ph1)
        step2 - taskset0: Reserve 4 cores (ph0)
        step3 - Release cores on taskset0
        step4 - taskset3: Reserve 2 cores (ph0)
        step5 - taskset4: 3 remaining, Reserve 3 cores (ph0+ph1)
        step5 - taskset5: No more cores
        """
        cpuInfo = os.path.join(os.path.dirname(__file__), 'cpuinfo', '_cpuinfo_shark_ht_8-4-2-2')
        self.fs.add_real_file(cpuInfo)
        self.machine.testInitMachineStats(cpuInfo)

        self.machine.setupTaskset()

        #-----------------------Core Map------------------------
        # phys 0             phys 1
        #   core 0             core 0
        #     proc 0             proc 4
        #     proc 8             proc 12
        #   core 1             core 1
        #     proc 1             proc 5
        #     proc 9             proc 13
        #   core 2             core 2
        #     proc 2             proc 6
        #     proc 10            proc 14
        #   core 3             core 3
        #     proc 3             proc 7
        #     proc 11            proc 15
        # ------------------------step1-------------------------
        def assertTaskSet(taskset_list):
            """Ensure all tasks are being allocated with the right thread pairs"""
            phys0 = [('0', '8'), ('1', '9'), ('10', '2'), ('11', '3')]
            phys1 = [('12', '4'), ('13', '5'), ('14', '6'), ('15', '7')]

            taskset_2_2 = list(zip(taskset_list[::2], taskset_list[1::2]))
            if taskset_2_2[0] in phys0:
                for t in taskset_2_2:
                    self.assertTrue(tuple(sorted(t)) in phys0, "%s not in %s" % (t, phys0))
            elif taskset_2_2[0] in phys1:
                for t in taskset_2_2:
                    self.assertTrue(tuple(sorted(t)) in phys1, "%s not in %s" % (t, phys1))

        tasksets0 = self.machine.reserveHT(300)
        self.assertIsNotNone(tasksets0)
        assertTaskSet(tasksets0.split(","))

        tasksets1 = self.machine.reserveHT(400)
        self.assertIsNotNone(tasksets1)
        assertTaskSet(tasksets1.split(","))

        # Make sure tastsets don't overlap
        self.assertTrue(set(tasksets0.split(',')).isdisjoint(tasksets1.split(',')))

        # ------------------------step3-------------------------
        # Releasing a physcore shouldn't impact other physcores
        self.machine.releaseHT(tasksets0)
        # pylint: disable=no-member
        self.assertTrue(1 in self.coreDetail.reserved_cores)

        # ------------------------step4-------------------------
        # phys_id 0
        #   - core_id 0
        #     - process_id 0
        #     - process_id 8
        #   - core_id 1
        #     - process_id 1
        #     - process_id 9
        tasksets3 = self.machine.reserveHT(200)
        assertTaskSet(tasksets3.split(","))

        # ------------------------step5-------------------------
        # Missing one core
        with self.assertRaises(rqd.rqexceptions.CoreReservationFailureException):
            tasksets4 = self.machine.reserveHT(300)


    def test_tags(self):
        tags = ["test1", "test2", "test3"]
        rqd.rqconstants.RQD_TAGS = " ".join(tags)

        machine = rqd.rqmachine.Machine(self.rqCore, self.coreDetail)

        self.assertTrue(all(tag in machine.__dict__['_Machine__renderHost'].tags for tag in tags))


@mock.patch('platform.system', new=mock.MagicMock(return_value='Linux'))
class CpuinfoTestsLinux(pyfakefs.fake_filesystem_unittest.TestCase):

    @mock.patch('platform.system', new=mock.MagicMock(return_value='Linux'))
    def setUp(self):
        self.setUpPyfakefs()
        self.fs.create_file('/proc/cpuinfo', contents=CPUINFO)
        self.loadavg = self.fs.create_file('/proc/loadavg', contents=LOADAVG_LOW_USAGE)
        self.procStat = self.fs.create_file('/proc/stat', contents=PROC_STAT)
        self.meminfo = self.fs.create_file('/proc/meminfo', contents=MEMINFO_MODERATE_USAGE)
        self.fs.add_real_directory(os.path.dirname(__file__))
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

    def __cpuinfoTestHelper(self, pathCpuInfo):
        # File format: _cpuinfo_dub_x-x-x where x-x-x is totalCores-coresPerProc-numProcs
        pathCpuInfo = os.path.join(os.path.dirname(__file__), 'cpuinfo', pathCpuInfo)
        self.meminfo.set_contents(MEMINFO_MODERATE_USAGE)
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
