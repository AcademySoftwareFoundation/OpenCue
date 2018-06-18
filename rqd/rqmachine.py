
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



"""
Machine information access module.

Project: RQD

Module: rqmachine.py

Contact: Middle-Tier 

SVN: $Id$
"""

import commands
import copy
import errno
import logging as log
import math
import os
import platform
import psutil
import re
import socket
import statvfs
import subprocess
import sys
import tempfile
import time
import traceback

if platform.system() == 'Linux':
    import resource
    import yaml

import rqconstants
import rqutil
import rqswap

if platform.system() == "win32":
    import win32process
    import win32api

import Ice
Ice.loadSlice("--all -I{PATH}/slice/spi -I{PATH}/slice/cue {PATH}/slice/cue/" \
              "rqd_ice.ice".replace("{PATH}", os.path.dirname(__file__)))
import cue.RqdIce as RqdIce
from cue.CueIce import HardwareState

KILOBYTE = 1024

class Machine:
    """Gathers information about the machine and resources"""
    def __init__(self, rq_core, coreInfo):
        """Machine class initialization
        @type   rq_core: RqCore
        @param  rq_core: Main RQD Object, used to access frames and nimby states
        @type  coreInfo: RqdIce.CoreDetail
        @param coreInfo: Object contains information on the state of all cores
        """
        self.__rq_core = rq_core
        self.__coreInfo = coreInfo

        if platform.system() == 'Linux':
            self.__vmstat = rqswap.VmStat()

        self.state = HardwareState.Up

        # renderHost
        self.__renderHost = RqdIce.RenderHost()
        self.__renderHost.attributes =  {}
        self.__initMachineTags()
        self.__initMachineStats()

        # bootReport
        self.__bootReport = RqdIce.BootReport()
        self.__bootReport.coreInfo = self.__coreInfo

        # hostReport
        self.__hostReport = RqdIce.HostReport()
        self.__hostReport.coreInfo = self.__coreInfo

        self.__pid_history = {}

        self.setupHT()

    def isNimbySafeToRunJobs(self):
        """Returns False if nimby should be triggered due to resource limits"""
        if platform.system() == "Linux":
            self.updateMachineStats()
            if self.__renderHost.freeMem < rqconstants.MINIMUM_MEM:
                return False
            if self.__renderHost.freeSwap < rqconstants.MINIMUM_SWAP:
                return False
        return True

    def isNimbySafeToUnlock(self):
        """Returns False if nimby should not unlock due to resource limits"""
        if not self.isNimbySafeToRunJobs():
            return False
        if self.getLoadAvg() / self.__coreInfo.totalCores > rqconstants.MAXIMUM_LOAD:
            return False
        return True

    @rqutil.Memoize
    def isDesktop(self):
        """Returns True if machine starts in run level 5 (X11)
           by checking /etc/inittab. False if not."""
        if platform.system() == "Linux":
            inittabFile = open(rqconstants.PATH_INITTAB, "r")
            for line in inittabFile:
                if line.startswith("id:5:initdefault:"):
                    return True
            if os.path.islink(rqconstants.PATH_INIT_TARGET):
                if os.path.realpath(rqconstants.PATH_INIT_TARGET).endswith('graphical.target'):
                    return True
        return False

    def isUserLoggedIn(self):
        # For non-headless systems, first check to see if there
        # is a user logged into the display.
        display_nums = []

        try:
            display_re = re.compile(r'X(\d+)')
            for displays in os.listdir('/tmp/.X11-unix'):
                m = display_re.match(displays)
                if not m:
                    continue
                display_nums.append(int(m.group(1)))
        except OSError as e:
            if e.errno != errno.ENOENT:
                raise

        if display_nums:
            # Check `who` output for a user associated with a display, like:
            #
            # (unknown) :0           2017-11-07 18:21 (:0)
            #
            # In this example, the user is '(unknown)'.
            for line in subprocess.check_output(['/usr/bin/who']).splitlines():
                for display_num in display_nums:
                    if '(:{})'.format(display_num) in line:
                        cols = line.split()
                        # Whitelist a user called '(unknown)' as this
                        # is what shows up when gdm is running and
                        # showing a login screen.
                        if cols[0] != '(unknown)':
                            log.warning(
                                'User {} logged into display :{}'.format(
                                    cols[0], display_num))
                            return True

            # When there is a display, the above code is considered
            # the authoritative check for a logged in user. The
            # code below gives false positives on a non-headless
            # system.
            return False

        # These process names imply a user is logged in.
        names = set(['kdesktop', 'gnome-session', 'startkde'])

        for proc in psutil.process_iter():
            proc_name = proc.name()
            for name in names:
                if name in proc_name:
                    return True
        return False

    def rss_update(self, frames):
        """Updates the rss and maxrss for all running frames"""
        if platform.system() != 'Linux':
            return

        pids = {}
        for pid in os.listdir("/proc"):
            if pid.isdigit():
                try:
                    statFile = open("/proc/%s/stat" % pid,"r")
                    statFields = statFile.read().split()
                    statFile.close()

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
                        "start_time": statFields[21]}
                except Exception, e:
                    pass

        try:
            now = int(time.time())
            pid_data = {"time": now}
            last_time = self.__pid_history.get("time")
            boot_time = self.getBootTime()

            values = frames.values()

            for frame in values:
                if frame.pid > 0:
                    session = str(frame.pid)
                    rss = 0
                    vsize = 0
                    pcpu = 0
                    if rqconstants.ENABLE_PTREE:
                        ptree = []
                    for pid, data in pids.iteritems():
                        if data["session"] == session:
                            try:
                                rss += int(data["rss"])
                                vsize += int(data["vsize"])

                                # jiffies used by this process, last two means that dead children are counted
                                total_time = int(data["utime"]) + \
                                            int(data["stime"]) + \
                                            int(data["cutime"]) + \
                                            int(data["cstime"])

                                # Seconds of process life, boot time is already in seconds
                                seconds = now - boot_time - \
                                        float(data["start_time"]) / rqconstants.SYS_HERTZ
                                if seconds:
                                    if self.__pid_history.has_key(pid):
                                        # Percent cpu using decaying average, 50% from 10 seconds ago, 50% from last 10 seconds:
                                        old_total_time, old_seconds, old_pid_pcpu = self.__pid_history[pid]
                                        #checking if already updated data
                                        if seconds != old_seconds:
                                            pid_pcpu = (total_time - old_total_time) / float(seconds - old_seconds)
                                            pcpu += (old_pid_pcpu + pid_pcpu) / 2 # %cpu
                                            pid_data[pid] = total_time, seconds, pid_pcpu
                                    else:
                                        pid_pcpu = total_time / seconds
                                        pcpu += pid_pcpu
                                        pid_data[pid] = total_time, seconds, pid_pcpu

                                if rqconstants.ENABLE_PTREE:
                                    ptree.append({"pid":pid, "seconds":seconds, "total_time":total_time})
                            except Exception as e:
                                log.warning('Failure with pid rss update due to: %s at %s' % \
                                            (e, traceback.extract_tb(sys.exc_info()[2])))

                    rss = (rss * resource.getpagesize()) / 1024
                    vsize = int(vsize/1024)

                    frame.rss = rss
                    frame.maxRss = max(rss, frame.maxRss)

                    frame.vsize = vsize
                    frame.maxVsize = max(vsize, frame.maxVsize)

                    frame.runFrame.attributes["pcpu"] = str(pcpu)

                    if rqconstants.ENABLE_PTREE:
                        frame.runFrame.attributes["ptree"] = str(yaml.load("list: %s" % ptree))

            # Store the current data for the next check
            self.__pid_history = pid_data
        except Exception, e:
            log.exception('Failure with rss update due to: {0}'.format(e))

    def getLoadAvg(self):
        """Returns average number of processes waiting to be served
           for the last 1 minute multiplied by 100."""
        if platform.system() == "Linux":
            loadAvgFile = open(rqconstants.PATH_LOADAVG, "r")
            loadAvg = int(float(loadAvgFile.read().split()[0]) * 100)
            if self.__enabledHT():
                loadAvg = loadAvg / 2
            loadAvg = loadAvg + rqconstants.LOAD_MODIFIER
            loadAvg = max(loadAvg, 0)
            return loadAvg
        return 0

    @rqutil.Memoize
    def getBootTime(self):
        """Returns epoch when the system last booted"""
        if platform.system() == "Linux":
            statFile = open(rqconstants.PATH_STAT, "r")
            for line in statFile:
                if line.startswith("btime"):
                    return int(line.split()[1])
        return 0

    @rqutil.Memoize
    def getGpuMemoryTotal(self):
        """Returns the total gpu memory in kb for CUE_GPU_MEMORY"""
        return self.__getGpuValues()['total']

    def getGpuMemory(self):
        """Returns the available gpu memory in kb for CUE_GPU_MEMORY"""
        return self.__getGpuValues()['free']

    def __getGpuValues(self):
        total = free = 0
        if not hasattr(self, 'gpuNotSupported'):
            if not hasattr(self, 'gpuResults'):
                self.gpuResults = {'total': 0, 'free': 0, 'updated': 0}
            if rqconstants.ALLOW_PLAYBLAST and not rqconstants.ALLOW_GPU:
                return {'total': 262144, 'free': 262144, 'updated': 0}
            if not rqconstants.ALLOW_GPU:
                self.gpuNotSupported = True
                return self.gpuResults
            if self.gpuResults['updated'] > time.time() - 60:
                return self.gpuResults
            try:
                # /shots/spi/home/bin/spinux1/cudaInfo
                # /shots/spi/home/bin/rhel7/cudaInfo
                cudaInfo = commands.getoutput('/usr/local/spi/rqd3/cudaInfo')
                if 'There is no device supporting CUDA' in cudaInfo:
                    self.gpuNotSupported = True
                else:
                    results = cudaInfo.splitlines()[-1].split()
                    #  TotalMem 1023 Mb  FreeMem 968 Mb
                    # The int(math.ceil(int(x) / 32.0) * 32) rounds up to the next multiple of 32
                    self.gpuResults['total'] = int(math.ceil(int(results[1]) / 32.0) * 32) * KILOBYTE
                    self.gpuResults['free'] = int(results[4]) * KILOBYTE
                    self.gpuResults['updated'] = time.time()
            except Exception, e:
                log.warning('Failed to get FreeMem from cudaInfo due to: %s at %s' % \
                            (e, traceback.extract_tb(sys.exc_info()[2])))
        return self.gpuResults

    def __getSwapout(self):
        if platform.system() == "Linux":
            try:
                return str(int(self.__vmstat.get_recent_pgout_rate()))
            except:
                return str(0)
        return str(0)

    @rqutil.Memoize
    def getTimezone(self):
        """Returns the desired timezone"""
        if time.tzname[0] == 'IST':
            return 'IST'
        else:
            return 'PST8PDT'

    @rqutil.Memoize
    def getHostname(self):
        """Returns the machine's fully qualified domain name"""
        return rqutil.getHostname()

    @rqutil.Memoize
    def getPathEnv(self):
        """Returns the correct path environment for the given machine"""
        if platform.system() == "Linux":
            return "/usr/local/spi/bin:/usr/local/psoft/bin:/usr/sbin:" \
                   "/usr/bsd:/usr/bin:/bin:/etc:/usr/etc:/usr/bin/X11"
        return ""

    @rqutil.Memoize
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
        self.__renderHost.tags = ["rqdv-%s" % rqconstants.VERSION]

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
        self.__renderHost.tags.append(os.uname()[2].replace(".EL.spi","").replace("smp",""))

    def testInitMachineStats(self, pathCpuInfo):
        self.__initMachineStats(pathCpuInfo=pathCpuInfo)
        return self.__renderHost, self.__coreInfo

    def __initMachineStats(self, pathCpuInfo=None):
        """Updates static machine information during initialization"""
        self.__renderHost.name = self.getHostname()
        self.__renderHost.bootTime = self.getBootTime()
        self.__renderHost.facility = rqconstants.FACILITY
        self.__renderHost.attributes['SP_OS'] = rqconstants.SP_OS

        self.updateMachineStats()

        __numProcs = __totalCores = 0
        if platform.system() == "Linux":
            # Reads static information for mcp
            mcpStat = os.statvfs(self.getTempPath())
            self.__renderHost.totalMcp = (mcpStat[statvfs.F_BLOCKS]
                                          * mcpStat[statvfs.F_BSIZE]) / KILOBYTE

            # Reads static information from /proc/cpuinfo
            cpuinfoFile = open(pathCpuInfo or rqconstants.PATH_CPUINFO, "r")
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
                    hyperthreadingMultipler =  (int(singleCore.get('siblings', '1'))
                                               / int(singleCore.get('cpu cores', '1')))

                    __totalCores += rqconstants.CORE_VALUE
                    if singleCore.has_key("core id") \
                       and singleCore.has_key("physical id") \
                       and not singleCore["physical id"] in procsFound:
                        procsFound.append(singleCore["physical id"])
                        __numProcs += 1
                    elif not singleCore.has_key("core id"):
                        __numProcs += 1
                    singleCore = {}
                # An entry without data
                elif len(lineList) == 1:
                    singleCore[lineList[0]] = ""

            # Reads static information from /proc/meminfo
            meminfoFile = open(rqconstants.PATH_MEMINFO, "r")
            for line in meminfoFile:
                if line.startswith("MemTotal"):
                    self.__renderHost.totalMem = int(line.split()[1])
                elif line.startswith("SwapTotal"):
                    self.__renderHost.totalSwap = int(line.split()[1])
            meminfoFile.close()

            self.__renderHost.attributes['totalGpu'] = str(self.getGpuMemoryTotal())
        else:
            hyperthreadingMultipler = 1

        if platform.system() == 'Windows':
            # Windows memory information
            stat = self.getWindowsMemory()
            TEMP_DEFAULT = 1048576
            self.__renderHost.totalMcp = TEMP_DEFAULT
            self.__renderHost.totalMem = int(stat.ullTotalPhys / 1024)
            self.__renderHost.totalSwap = int(stat.ullTotalPageFile / 1024)

            # Windows CPU information
            import multiprocessing
            __totalCores = multiprocessing.cpu_count() * 100
            if __totalCores > 1200:
                __totalCores = __totalCores / 2
                __numProcs = 2

        # All other systems will just have one proc/core
        if not __numProcs or not __totalCores:
            __numProcs = 1
            __totalCores = rqconstants.CORE_VALUE

        if not rqconstants.OVERRIDE_MEMORY is None:
            log.warning("Manually overriding the total memory")
            self.__renderHost.totalMem = rqconstants.OVERRIDE_MEMORY

        if not rqconstants.OVERRIDE_CORES is None:
            log.warning("Manually overriding the number of reported cores")
            __totalCores = rqconstants.OVERRIDE_CORES * rqconstants.CORE_VALUE

        if not rqconstants.OVERRIDE_PROCS is None:
            log.warning("Manually overriding the number of reported procs")
            __numProcs = rqconstants.OVERRIDE_PROCS

        # Don't report/reserve cores added due to hyperthreading
        __totalCores = __totalCores / hyperthreadingMultipler

        self.__coreInfo.idleCores = __totalCores
        self.__coreInfo.totalCores = __totalCores
        self.__renderHost.numProcs = __numProcs
        self.__renderHost.coresPerProc = __totalCores / __numProcs

        if hyperthreadingMultipler > 1:
           self.__renderHost.attributes['hyperthreadingMultiplier'] = str(hyperthreadingMultipler)

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
                    return super(MEMORYSTATUSEX, self).__init__()

            self.__windowsStat = MEMORYSTATUSEX()
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(self.__windowsStat))
        return self.__windowsStat

    def updateMachineStats(self):
        """Updates dynamic machine information during runtime"""
        if platform.system() == "Linux":
            # Reads dynamic information for mcp
            mcpStat = os.statvfs(self.getTempPath())
            self.__renderHost.freeMcp = (mcpStat[statvfs.F_BAVAIL]
                                         * mcpStat[statvfs.F_BSIZE]) / KILOBYTE

            # Reads dynamic information from /proc/meminfo
            meminfoFile = open(rqconstants.PATH_MEMINFO, "r")
            for line in meminfoFile:
                if line.startswith("MemFree"):
                    freeMem = int(line.split()[1])
                elif line.startswith("SwapFree"):
                    freeSwapMem = int(line.split()[1])
                elif line.startswith("Cached"):
                    cachedMem = int(line.split()[1])
            meminfoFile.close()
            self.__renderHost.freeSwap = freeSwapMem
            self.__renderHost.freeMem = freeMem + cachedMem
            self.__renderHost.attributes['freeGpu'] = str(self.getGpuMemory())
            self.__renderHost.attributes['swapout'] = self.__getSwapout()

        elif platform.system() == 'Windows':
            TEMP_DEFAULT = 1048576
            stats = self.getWindowsMemory()
            self.__renderHost.freeMcp = TEMP_DEFAULT
            self.__renderHost.freeSwap = int(stats.ullAvailPageFile / 1024)
            self.__renderHost.freeMem = int(stats.ullAvailPhys /1024)

        # Updates dyanimic information
        self.__renderHost.load = self.getLoadAvg()
        self.__renderHost.nimbyEnabled = self.__rq_core.nimby.active
        self.__renderHost.nimbyLocked = self.__rq_core.nimby.locked
        self.__renderHost.state = self.state

    def getHostInfo(self):
        """Updates and returns the renderHost struct"""
        self.updateMachineStats()
        return self.__renderHost

    def getHostReport(self):
        """Updates and returns the hostReport struct"""
        # .hostInfo
        self.__hostReport.host = self.getHostInfo()

        # .frames
        self.__hostReport.frames = []
        for frameKey in self.__rq_core.getFrameKeys():
            try:
                info = self.__rq_core.getFrame(frameKey).runningFrameInfo()
                self.__hostReport.frames.append(info)
            except KeyError:
                pass

        return self.__hostReport

    def getBootReport(self):
        """Updates and returns the bootReport struct"""
        # .hostInfo
        self.__bootReport.host = self.getHostInfo()

        return self.__bootReport

    def __enabledHT(self):
        return self.__renderHost.attributes.has_key('hyperthreadingMultiplier')

    def setupHT(self):
        """ Setup rqd for hyper-threading """

        if self.__enabledHT():
            self.__coreInfo.tasksets = set(range(self.__coreInfo.totalCores / 100))

    def reserveHT(self, reservedCores):
        """ Reserve cores for use by taskset
        taskset -c 0,1,8,9 COMMAND
        Not thread save, use with locking.
        @type   reservedCores: int
        @param  reservedCores: The total physical cores reserved by the frame.
        @rtype:  string
        @return: The cpu-list for taskset -c
        """

        if not self.__enabledHT():
            return None

        if reservedCores % 100:
            log.debug('Taskset: Can not reserveHT with fractional cores')
            return None

        log.debug('Taskset: Requesting reserve of %s' % (reservedCores / 100))

        if len(self.__coreInfo.tasksets) < reservedCores / 100:
            err = 'Not launching, insufficient hyperthreading cores to reserve based on reservedCores'
            log.critical(err)
            raise RqdIce.CoreReservationFailureException(err)

        tasksets = []
        for x in range(reservedCores / 100):
            core = self.__coreInfo.tasksets.pop()
            tasksets.append(str(core))
            tasksets.append(str(core + self.__coreInfo.totalCores / 100))

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
            if int(core) < self.__coreInfo.totalCores / 100:
                self.__coreInfo.tasksets.add(int(core))

