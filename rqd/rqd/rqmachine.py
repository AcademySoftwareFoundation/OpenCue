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
"""


from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

from future import standard_library

standard_library.install_aliases()
from builtins import str, range, object

import errno
import logging as log
import os
import platform
import psutil
import re
import subprocess
import sys
import time
import traceback

if platform.system() in ('Linux', 'Darwin'):
    import resource
    import yaml

import rqd.compiled_proto.host_pb2
from rqd.compiled_proto import report_pb2
import rqd.rqconstants
import rqd.rqexceptions
from rqd.rqplatform import current_platform
import rqd.rqutil

KILOBYTE = 1024


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

        self.state = rqd.compiled_proto.host_pb2.UP

        self.__renderHost = report_pb2.RenderHost()
        self.__initMachineTags()
        self.__initMachineStats()

        self.__bootReport = report_pb2.BootReport()
        self.__bootReport.core_info.CopyFrom(self.__coreInfo)

        self.__hostReport = report_pb2.HostReport()
        self.__hostReport.core_info.CopyFrom(self.__coreInfo)

        self.__pidHistory = {}

        self.setupHT()

    def isNimbySafeToRunJobs(self):
        """Returns False if nimby should be triggered due to resource limits"""
        if platform.system() == "Linux":
            self.updateMachineStats(self.__renderHost)
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
                        # Whitelist a user called '(unknown)' as this
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
        return current_platform.getLoadAvg()

    @rqd.rqutil.Memoize
    def getBootTime(self):
        """Returns epoch when the system last booted"""
        return current_platform.getBootTime()

    @rqd.rqutil.Memoize
    def getGpuMemoryTotal(self):
        """Returns the total gpu memory in kb for CUE_GPU_MEMORY"""
        return current_platform.getMemoryInfo().total_gpu

    def getGpuMemory(self):
        """Returns the available gpu memory in kb for CUE_GPU_MEMORY"""
        return current_platform.getMemoryInfo().free_gpu

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
        return current_platform.getHostname()

    @rqd.rqutil.Memoize
    def getPathEnv(self):
        """Returns the correct path environment for the given machine"""
        if platform.system() == 'Linux':
            return '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'
        return ''

    @rqd.rqutil.Memoize
    def getTempPath(self):
        return current_platform.getTempPath()

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

    def __initMachineStats(self):
        """Updates static machine information during initialization"""
        self.__renderHost.name = self.getHostname()
        self.__renderHost.boot_time = self.getBootTime()
        self.__renderHost.facility = rqd.rqconstants.FACILITY
        self.__renderHost.attributes['SP_OS'] = rqd.rqconstants.SP_OS

        self.updateMachineStats(self.__renderHost)

        cpuInfo = current_platform.getCpuInfo()
        totalCores = cpuInfo.logical_cores * rqd.rqconstants.CORE_VALUE
        numProcs = cpuInfo.physical_cpus
        hyperthreadingMultiplier = cpuInfo.hyperthreading_multiplier

        # Don't report/reserve cores added due to hyperthreading
        totalCores = totalCores // hyperthreadingMultiplier

        self.__coreInfo.idle_cores = totalCores
        self.__coreInfo.total_cores = totalCores
        self.__renderHost.num_procs = numProcs
        self.__renderHost.cores_per_proc = totalCores // numProcs

        if hyperthreadingMultiplier > 1:
           self.__renderHost.attributes['hyperthreadingMultiplier'] = str(hyperthreadingMultiplier)

    def updateMachineStats(self, renderHost):
        # type: (report_pb2.RenderHost) -> None
        """Updates dynamic machine information during runtime"""

        diskInfo = current_platform.getDiskInfo()
        renderHost.total_mcp = diskInfo.total_mcp
        renderHost.free_mcp = diskInfo.free_mcp

        memInfo = current_platform.getMemoryInfo()
        renderHost.total_mem = memInfo.total_mem
        renderHost.free_mem = memInfo.free_mem
        renderHost.total_swap = memInfo.total_swap
        renderHost.free_swap = memInfo.free_swap
        renderHost.attributes['freeGpu'] = str(memInfo.free_gpu)
        renderHost.attributes['swapout'] = str(memInfo.swap_out)

        # Updates dynamic information
        renderHost.load = self.getLoadAvg()
        renderHost.nimby_enabled = self.__rqCore.nimby.active
        renderHost.nimby_locked = self.__rqCore.nimby.locked
        renderHost.state = self.state

    def getHostInfo(self):
        """Updates the renderHost struct"""
        self.updateMachineStats(self.__renderHost)
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
