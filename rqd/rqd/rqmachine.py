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


"""
Machine information access module.
"""


from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

from future import standard_library
standard_library.install_aliases()
from builtins import str
from builtins import range
from builtins import object

import errno
import logging as log
import math
import os
import platform
import psutil
import re
import subprocess
import sys
import tempfile
import time
import traceback

if platform.system() in ('Linux', 'Darwin'):
    import resource
    import yaml
elif platform.system() == "win32":
    import win32process
    import win32api

import rqd.compiled_proto.host_pb2
import rqd.compiled_proto.report_pb2
import rqd.rqconstants
import rqd.rqexceptions
import rqd.rqswap
import rqd.rqutil


KILOBYTE = 1024
GPU_DEFAULT = {'count': 0, 'total': 0, 'free': 0, 'updated': 0}


class Machine(object):
    """Gathers information about the machine and resources"""
    def __init__(self, rqCore, coreInfo):
        """Machine class initialization
        @type   rqCore: rqd.rqcore.RqCore
        @param  rqCore: Main RQD Object, used to access frames and nimby states
        @type  coreInfo: rqd.compiled_proto.report_pb2.CoreDetail
        @param coreInfo: Object contains information on the state of all cores
        """
        self.__rqCore = rqCore
        self.__coreInfo = coreInfo
        self.__tasksets = set()
        self.__gpusets = set()

        if platform.system() == 'Linux':
            self.__vmstat = rqd.rqswap.VmStat()

        self.state = rqd.compiled_proto.host_pb2.UP

        self.__renderHost = rqd.compiled_proto.report_pb2.RenderHost()
        self.__initMachineTags()
        self.__initMachineStats()

        self.__bootReport = rqd.compiled_proto.report_pb2.BootReport()
        self.__bootReport.core_info.CopyFrom(self.__coreInfo)

        self.__hostReport = rqd.compiled_proto.report_pb2.HostReport()
        self.__hostReport.core_info.CopyFrom(self.__coreInfo)

        self.__pidHistory = {}

        self.setupHT()
        self.setupGpu()

    def isNimbySafeToRunJobs(self):
        """Returns False if nimby should be triggered due to resource limits"""
        if platform.system() == "Linux":
            self.updateMachineStats()
            if self.__renderHost.free_mem < rqd.rqconstants.MINIMUM_MEM:
                return False
            if self.__renderHost.free_swap < rqd.rqconstants.MINIMUM_SWAP:
                return False
        return True

    def isNimbySafeToUnlock(self):
        """Returns False if nimby should not unlock due to resource limits"""
        if not self.isNimbySafeToRunJobs():
            return False
        if self.getLoadAvg() / self.__coreInfo.total_cores > rqd.rqconstants.MAXIMUM_LOAD:
            return False
        return True

    @rqd.rqutil.Memoize
    def isDesktop(self):
        """Returns True if machine starts in run level 5 (X11)
           by checking /etc/inittab. False if not."""
        if rqd.rqconstants.OVERRIDE_IS_DESKTOP:
            return True
        if platform.system() == "Linux" and os.path.exists(rqd.rqconstants.PATH_INITTAB):
            inittabFile = open(rqd.rqconstants.PATH_INITTAB, "r")
            for line in inittabFile:
                if line.startswith("id:5:initdefault:"):
                    return True
            if os.path.islink(rqd.rqconstants.PATH_INIT_TARGET):
                if os.path.realpath(rqd.rqconstants.PATH_INIT_TARGET).endswith('graphical.target'):
                    return True
        return False

    def isUserLoggedIn(self):
        # For non-headless systems, first check to see if there
        # is a user logged into the display.
        displayNums = []

        try:
            displayRe = re.compile(r'X(\d+)')
            for displays in os.listdir('/tmp/.X11-unix'):
                m = displayRe.match(displays)
                if not m:
                    continue
                displayNums.append(int(m.group(1)))
        except OSError as e:
            if e.errno != errno.ENOENT:
                raise

        if displayNums:
            # Check `who` output for a user associated with a display, like:
            #
            # (unknown) :0           2017-11-07 18:21 (:0)
            #
            # In this example, the user is '(unknown)'.
            for line in subprocess.check_output(['/usr/bin/who']).splitlines():
                for displayNum in displayNums:
                    if '(:{})'.format(displayNum) in line:
                        cols = line.split()
                        # Acceptlist a user called '(unknown)' as this
                        # is what shows up when gdm is running and
                        # showing a login screen.
                        if cols[0] != '(unknown)':
                            log.warning(
                                'User {} logged into display :{}'.format(
                                    cols[0], displayNum))
                            return True

            # When there is a display, the above code is considered
            # the authoritative check for a logged in user. The
            # code below gives false positives on a non-headless
            # system.
            return False

        # These process names imply a user is logged in.
        names = {'kdesktop', 'gnome-session', 'startkde'}

        for proc in psutil.process_iter():
            procName = proc.name()
            for name in names:
                if name in procName:
                    return True
        return False

    def rssUpdate(self, frames):
        """Updates the rss and maxrss for all running frames"""
        if platform.system() != 'Linux':
            return

        pids = {}
        for pid in os.listdir("/proc"):
            if pid.isdigit():
                try:
                    with open("/proc/%s/stat" % pid, "r") as statFile:
                        statFields = statFile.read().split()

                    # See "man proc"
                    pids[pid] = {
                        "session": statFields[5],
                        "vsize": statFields[22],
                        "rss": statFields[23],
                        # These are needed to compute the cpu used
                        "utime": statFields[13],
                        "stime": statFields[14],
                        "cutime": statFields[15],
                        "cstime": statFields[16],
                        # The time in jiffies the process started
                        # after system boot.
                        "start_time": statFields[21],
                    }

                except Exception as e:
                    log.exception('failed to read stat file for pid %s' % pid)

        try:
            now = int(time.time())
            pidData = {"time": now}
            bootTime = self.getBootTime()

            values = list(frames.values())

            for frame in values:
                if frame.pid > 0:
                    session = str(frame.pid)
                    rss = 0
                    vsize = 0
                    pcpu = 0
                    if rqd.rqconstants.ENABLE_PTREE:
                        ptree = []
                    for pid, data in pids.items():
                        if data["session"] == session:
                            try:
                                rss += int(data["rss"])
                                vsize += int(data["vsize"])

                                # jiffies used by this process, last two means that dead children are counted
                                totalTime = int(data["utime"]) + \
                                            int(data["stime"]) + \
                                            int(data["cutime"]) + \
                                            int(data["cstime"])

                                # Seconds of process life, boot time is already in seconds
                                seconds = now - bootTime - \
                                          float(data["start_time"]) / rqd.rqconstants.SYS_HERTZ
                                if seconds:
                                    if pid in self.__pidHistory:
                                        # Percent cpu using decaying average, 50% from 10 seconds ago, 50% from last 10 seconds:
                                        oldTotalTime, oldSeconds, oldPidPcpu = self.__pidHistory[pid]
                                        #checking if already updated data
                                        if seconds != oldSeconds:
                                            pidPcpu = (totalTime - oldTotalTime) / float(seconds - oldSeconds)
                                            pcpu += (oldPidPcpu + pidPcpu) / 2 # %cpu
                                            pidData[pid] = totalTime, seconds, pidPcpu
                                    else:
                                        pidPcpu = totalTime / seconds
                                        pcpu += pidPcpu
                                        pidData[pid] = totalTime, seconds, pidPcpu

                                if rqd.rqconstants.ENABLE_PTREE:
                                    ptree.append({"pid": pid, "seconds": seconds, "total_time": totalTime})
                            except Exception as e:
                                log.warning('Failure with pid rss update due to: %s at %s' % \
                                            (e, traceback.extract_tb(sys.exc_info()[2])))

                    rss = (rss * resource.getpagesize()) // 1024
                    vsize = int(vsize/1024)

                    frame.rss = rss
                    frame.maxRss = max(rss, frame.maxRss)

                    frame.vsize = vsize
                    frame.maxVsize = max(vsize, frame.maxVsize)

                    frame.runFrame.attributes["pcpu"] = str(pcpu)

                    if rqd.rqconstants.ENABLE_PTREE:
                        frame.runFrame.attributes["ptree"] = str(yaml.load("list: %s" % ptree,
                                                                           Loader=yaml.SafeLoader))

            # Store the current data for the next check
            self.__pidHistory = pidData

        except Exception as e:
            log.exception('Failure with rss update due to: {0}'.format(e))

    def getLoadAvg(self):
        """Returns average number of processes waiting to be served
           for the last 1 minute multiplied by 100."""
        if platform.system() == "Linux":
            loadAvgFile = open(rqd.rqconstants.PATH_LOADAVG, "r")
            loadAvg = int(float(loadAvgFile.read().split()[0]) * 100)
            if self.__enabledHT():
                loadAvg = loadAvg // 2
            loadAvg = loadAvg + rqd.rqconstants.LOAD_MODIFIER
            loadAvg = max(loadAvg, 0)
            return loadAvg
        return 0

    @rqd.rqutil.Memoize
    def getBootTime(self):
        """Returns epoch when the system last booted"""
        if platform.system() == "Linux":
            statFile = open(rqd.rqconstants.PATH_STAT, "r")
            for line in statFile:
                if line.startswith("btime"):
                    return int(line.split()[1])
        return 0

    @rqutil.Memoize
    def getGpuCount(self):
        """Returns the total gpu's on the machine"""
        return self.__getGpuValues()['count']

    @rqutil.Memoize
    def getGpuMemoryTotal(self):
        """Returns the total gpu memory in kb for CUE_GPU_MEMORY"""
        return self.__getGpuValues()['total']

    def getGpuMemoryFree(self):
        """Returns the available gpu memory in kb for CUE_GPU_MEMORY"""
        return self.__getGpuValues()['free']

    def __getGpuValues(self):
        if not hasattr(self, 'gpuNotSupported'):
            if not hasattr(self, 'gpuResults'):
                self.gpuResults = GPU_DEFAULT
            if not rqconstants.ALLOW_GPU:
                self.gpuNotSupported = True
                return self.gpuResults
            if self.gpuResults['updated'] > int(time.time()) - 60:
                return self.gpuResults
            try:
                nvidia_smi = commands.getoutput('nvidia-smi --query-gpu=memory.total,memory.free,count --format=csv,noheader')
                total = 0
                free = 0
                count = 0
                for line in nvidia_smi.splitlines():
                    l = line.split()
                    total += math.ceil(int(l[0]) * 1048.576)
                    free += math.ceil(int(l[2]) * 1048.576)
                    count = int(l[-1])

                self.gpuResults['total'] = int(total)
                self.gpuResults['free'] = int(free)
                self.gpuResults['count'] = count
                self.gpuResults['updated'] = int(time.time())
            except Exception, e:
                self.gpuNotSupported = True
                self.gpuResults = GPU_DEFAULT
                log.warning('Failed to get FreeMem from cudaInfo due to: %s at %s' % \
                            (e, traceback.extract_tb(sys.exc_info()[2])))
        else:
            self.gpuResults = GPU_DEFAULT
        return self.gpuResults

    def __getSwapout(self):
        if platform.system() == "Linux":
            try:
                return str(int(self.__vmstat.getRecentPgoutRate()))
            except:
                return str(0)
        return str(0)

    @rqd.rqutil.Memoize
    def getTimezone(self):
        """Returns the desired timezone"""
        if time.tzname[0] == 'IST':
            return 'IST'
        else:
            return 'PST8PDT'

    @rqd.rqutil.Memoize
    def getHostname(self):
        """Returns the machine's fully qualified domain name"""
        return rqd.rqutil.getHostname()

    @rqd.rqutil.Memoize
    def getPathEnv(self):
        """Returns the correct path environment for the given machine"""
        if platform.system() == 'Linux':
            return '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'
        return ''

    @rqd.rqutil.Memoize
    def getTempPath(self):
        """Returns the correct mcp path for the given machine"""
        if platform.system() == "win32":
            return win32api.GetTempPath()
        elif os.path.isdir("/mcp/"):
            return "/mcp/"
        return '%s/' % tempfile.gettempdir()

    def reboot(self):
        """Reboots the machine immediately"""
        if platform.system() == "Linux":
            log.warning("Rebooting machine")
            subprocess.Popen(['/usr/bin/sudo','/sbin/reboot', '-f'])

    def __initMachineTags(self):
        """Sets the hosts tags"""
        self.__renderHost.tags.append("rqdv-%s" % rqd.rqconstants.VERSION)

        # Tag with desktop if it is a desktop
        if self.isDesktop():
            self.__renderHost.tags.append("desktop")

        if platform.system() == 'Windows':
            self.__renderHost.tags.append("windows")
            return

        if os.uname()[-1] in ("i386", "i686"):
            self.__renderHost.tags.append("32bit")
        elif os.uname()[-1] == "x86_64":
            self.__renderHost.tags.append("64bit")
        self.__renderHost.tags.append(os.uname()[2].replace(".EL.spi", "").replace("smp", ""))

    def testInitMachineStats(self, pathCpuInfo):
        self.__initMachineStats(pathCpuInfo=pathCpuInfo)
        return self.__renderHost, self.__coreInfo

    def __initMachineStats(self, pathCpuInfo=None):
        """Updates static machine information during initialization"""
        self.__renderHost.name = self.getHostname()
        self.__renderHost.boot_time = self.getBootTime()
        self.__renderHost.facility = rqd.rqconstants.FACILITY
        self.__renderHost.attributes['SP_OS'] = rqd.rqconstants.SP_OS

        self.updateMachineStats()

        __numProcs = __totalCores = 0
        if platform.system() == "Linux" or pathCpuInfo is not None:
            # Reads static information for mcp
            mcpStat = os.statvfs(self.getTempPath())
            self.__renderHost.total_mcp = mcpStat.f_blocks * mcpStat.f_frsize // KILOBYTE

            # Reads static information from /proc/cpuinfo
            with open(pathCpuInfo or rqd.rqconstants.PATH_CPUINFO, "r") as cpuinfoFile:
                singleCore = {}
                procsFound = []
                for line in cpuinfoFile:
                    lineList = line.strip().replace("\t","").split(": ")
                    # A normal entry added to the singleCore dictionary
                    if len(lineList) >= 2:
                        singleCore[lineList[0]] = lineList[1]
                    # The end of a processor block
                    elif lineList == ['']:
                        # Check for hyper-threading
                        hyperthreadingMultiplier = (int(singleCore.get('siblings', '1'))
                                                    // int(singleCore.get('cpu cores', '1')))

                        __totalCores += rqd.rqconstants.CORE_VALUE
                        if "core id" in singleCore \
                           and "physical id" in singleCore \
                           and not singleCore["physical id"] in procsFound:
                            procsFound.append(singleCore["physical id"])
                            __numProcs += 1
                        elif "core id" not in singleCore:
                            __numProcs += 1
                        singleCore = {}
                    # An entry without data
                    elif len(lineList) == 1:
                        singleCore[lineList[0]] = ""
        else:
            hyperthreadingMultiplier = 1

        if platform.system() == 'Windows':
            # Windows memory information
            stat = self.getWindowsMemory()
            TEMP_DEFAULT = 1048576
            self.__renderHost.total_mcp = TEMP_DEFAULT
            self.__renderHost.total_mem = int(stat.ullTotalPhys / 1024)
            self.__renderHost.total_swap = int(stat.ullTotalPageFile / 1024)

            # Windows CPU information
            import psutil
            logical_core_count = psutil.cpu_count(logical=True)
            actual_core_count = psutil.cpu_count(logical=False)
            hyperthreadingMultiplier = logical_core_count // actual_core_count

            __totalCores = logical_core_count * rqd.rqconstants.CORE_VALUE
            __numProcs = 1  # TODO: figure out how to count sockets in Python


        # All other systems will just have one proc/core
        if not __numProcs or not __totalCores:
            __numProcs = 1
            __totalCores = rqd.rqconstants.CORE_VALUE

        if rqd.rqconstants.OVERRIDE_MEMORY is not None:
            log.warning("Manually overriding the total memory")
            self.__renderHost.total_mem = rqd.rqconstants.OVERRIDE_MEMORY

        if rqd.rqconstants.OVERRIDE_CORES is not None:
            log.warning("Manually overriding the number of reported cores")
            __totalCores = rqd.rqconstants.OVERRIDE_CORES * rqd.rqconstants.CORE_VALUE

        if rqd.rqconstants.OVERRIDE_PROCS is not None:
            log.warning("Manually overriding the number of reported procs")
            __numProcs = rqd.rqconstants.OVERRIDE_PROCS

        # Don't report/reserve cores added due to hyperthreading
        __totalCores = __totalCores // hyperthreadingMultiplier

        self.__coreInfo.idle_cores = __totalCores
        self.__coreInfo.total_cores = __totalCores
        self.__renderHost.num_procs = __numProcs
        self.__renderHost.cores_per_proc = __totalCores // __numProcs

        if hyperthreadingMultiplier > 1:
           self.__renderHost.attributes['hyperthreadingMultiplier'] = str(hyperthreadingMultiplier)

    def getWindowsMemory(self):
        # From http://stackoverflow.com/questions/2017545/get-memory-usage-of-computer-in-windows-with-python
        import ctypes
        if not hasattr(self, '__windowsStat'):
            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_uint),
                            ("dwMemoryLoad", ctypes.c_uint),
                            ("ullTotalPhys", ctypes.c_ulonglong),
                            ("ullAvailPhys", ctypes.c_ulonglong),
                            ("ullTotalPageFile", ctypes.c_ulonglong),
                            ("ullAvailPageFile", ctypes.c_ulonglong),
                            ("ullTotalVirtual", ctypes.c_ulonglong),
                            ("ullAvailVirtual", ctypes.c_ulonglong),
                            ("sullAvailExtendedVirtual", ctypes.c_ulonglong),]

                def __init__(self):
                    # have to initialize this to the size of MEMORYSTATUSEX
                    self.dwLength = 2*4 + 7*8     # size = 2 ints, 7 longs
                    super(MEMORYSTATUSEX, self).__init__()

            self.__windowsStat = MEMORYSTATUSEX()
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(self.__windowsStat))
        return self.__windowsStat

    def updateMacMemory(self):
        memsizeOutput = subprocess.getoutput('sysctl hw.memsize').strip()
        memsizeRegex = re.compile(r'^hw.memsize: (?P<totalMemBytes>[\d]+)$')
        memsizeMatch = memsizeRegex.match(memsizeOutput)
        if memsizeMatch:
            self.__renderHost.total_mem = int(memsizeMatch.group('totalMemBytes')) // 1024
        else:
            self.__renderHost.total_mem = 0

        vmStatLines = subprocess.getoutput('vm_stat').split('\n')
        lineRegex = re.compile(r'^(?P<field>.+):[\s]+(?P<pages>[\d]+).$')
        vmStats = {}
        for line in vmStatLines[1:-2]:
            match = lineRegex.match(line)
            if match:
                vmStats[match.group('field')] = int(match.group('pages')) * 4096

        freeMemory = vmStats.get("Pages free", 0) // 1024
        inactiveMemory = vmStats.get("Pages inactive", 0) // 1024
        self.__renderHost.free_mem = freeMemory + inactiveMemory

        swapStats = subprocess.getoutput('sysctl vm.swapusage').strip()
        swapRegex = re.compile(r'^.* free = (?P<freeMb>[\d]+)M .*$')
        swapMatch = swapRegex.match(swapStats)
        if swapMatch:
            self.__renderHost.free_swap = int(float(swapMatch.group('freeMb')) * 1024)
        else:
            self.__renderHost.free_swap = 0

    def updateMachineStats(self):
        """Updates dynamic machine information during runtime"""
        if platform.system() == "Linux":
            # Reads dynamic information for mcp
            mcpStat = os.statvfs(self.getTempPath())
            self.__renderHost.free_mcp = (mcpStat.f_bavail * mcpStat.f_bsize) // KILOBYTE

            # Reads dynamic information from /proc/meminfo
            with open(rqd.rqconstants.PATH_MEMINFO, "r") as fp:
                for line in fp:
                    if line.startswith("MemFree"):
                        freeMem = int(line.split()[1])
                    elif line.startswith("SwapFree"):
                        freeSwapMem = int(line.split()[1])
                    elif line.startswith("Cached"):
                        cachedMem = int(line.split()[1])
                    elif line.startswith("MemTotal"):
                        self.__renderHost.total_mem = int(line.split()[1])

            self.__renderHost.free_swap = freeSwapMem
            self.__renderHost.free_mem = freeMem + cachedMem
            self.__renderHost.total_gpu_memory = self.getGpuMemoryTotal()
            self.__renderHost.free_gpu_memory = self.getGpuMemoryFree()

            self.__renderHost.attributes['freeGpu'] = str(self.getGpuMemory())
            self.__renderHost.attributes['swapout'] = self.__getSwapout()

        elif platform.system() == 'Darwin':
            self.updateMacMemory()

        elif platform.system() == 'Windows':
            TEMP_DEFAULT = 1048576
            stats = self.getWindowsMemory()
            self.__renderHost.free_mcp = TEMP_DEFAULT
            self.__renderHost.free_swap = int(stats.ullAvailPageFile / 1024)
            self.__renderHost.free_mem = int(stats.ullAvailPhys / 1024)

        # Updates dynamic information
        self.__renderHost.load = self.getLoadAvg()
        self.__renderHost.nimby_enabled = self.__rqCore.nimby.active
        self.__renderHost.nimby_locked = self.__rqCore.nimby.locked
        self.__renderHost.state = self.state

    def getHostInfo(self):
        """Updates and returns the renderHost struct"""
        self.updateMachineStats()
        return self.__renderHost

    def getHostReport(self):
        """Updates and returns the hostReport struct"""
        self.__hostReport.host.CopyFrom(self.getHostInfo())

        self.__hostReport.ClearField('frames')
        for frameKey in self.__rqCore.getFrameKeys():
            try:
                info = self.__rqCore.getFrame(frameKey).runningFrameInfo()
                self.__hostReport.frames.extend([info])
            except KeyError:
                pass

        self.__hostReport.core_info.CopyFrom(self.__rqCore.getCoreInfo())

        return self.__hostReport

    def getBootReport(self):
        """Updates and returns the bootReport struct"""
        self.__bootReport.host.CopyFrom(self.getHostInfo())

        return self.__bootReport

    def __enabledHT(self):
        return 'hyperthreadingMultiplier' in self.__renderHost.attributes

    def setupHT(self):
        """ Setup rqd for hyper-threading """

        if self.__enabledHT():
            self.__tasksets = set(range(self.__coreInfo.total_cores // 100))

    def setupGpu(self):
        """ Setup rqd for Gpus """
        self.__gpusets = set(range(self.getGpuCount()))

    def reserveHT(self, reservedCores):
        """ Reserve cores for use by taskset
        taskset -c 0,1,8,9 COMMAND
        Not thread save, use with locking.
        @type   reservedCores: int
        @param  reservedCores: The total physical cores reserved by the frame.
        :rtype:  string
        @return: The cpu-list for taskset -c
        """

        if not self.__enabledHT():
            return None

        if reservedCores % 100:
            log.debug('Taskset: Can not reserveHT with fractional cores')
            return None

        log.debug('Taskset: Requesting reserve of %d' % (reservedCores // 100))

        if len(self.__tasksets) < reservedCores // 100:
            err = 'Not launching, insufficient hyperthreading cores to reserve based on reservedCores'
            log.critical(err)
            raise rqd.rqexceptions.CoreReservationFailureException(err)

        tasksets = []
        for x in range(reservedCores // 100):
            core = self.__tasksets.pop()
            tasksets.append(str(core))
            tasksets.append(str(core + self.__coreInfo.total_cores // 100))

        log.debug('Taskset: Reserving cores - %s' % ','.join(tasksets))

        return ','.join(tasksets)

    def releaseHT(self, reservedHT):
        """ Release cores used by taskset
        Format: 0,1,8,9
        Not thread safe, use with locking.
        @type:  string
        @param: The cpu-list used for taskset to release. ex: '0,8,1,9'
        """

        if not self.__enabledHT():
            return None

        log.debug('Taskset: Releasing cores - %s' % reservedHT)
        for core in reservedHT.split(','):
            if int(core) < self.__coreInfo.total_cores // 100:
                self.__tasksets.add(int(core))

    def reserveGpu(self, reservedGpu):
        if len(self.__gpusets) < reservedGpu:
            err = 'Not launching, insufficient GPUs to reserve based on reservedGpu'
            log.critical(err)
            raise CoreReservationFailureException(err)

        gpusets = []
        for x in range(reservedGpu):
            gpu = self.__gpusets.pop()
            gpusets.append(str(gpu))

        return ','.join(gpusets)

    def releaseGpu(self, reservedGpu):
        log.debug('GPU set: Releasing gpu - %s' % reservedGpu)
        for gpu in reservedGpu.split(','):
            if int(gpu) < self.getGpuCount():
                self.__gpusets.add(int(gpu))
