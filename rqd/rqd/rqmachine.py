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


"""Machine information access module."""


from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

# pylint: disable=wrong-import-position
from future import standard_library
standard_library.install_aliases()
# pylint: enable=wrong-import-position

from builtins import str
from builtins import range
from builtins import object

import ctypes
import errno
import logging
import math
import os
import platform
import re
import subprocess
import sys
import tempfile
import time
import traceback
import warnings

# pylint: disable=import-error,wrong-import-position
if platform.system() in ('Linux', 'Darwin'):
    import resource
elif platform.system() == "Windows":
    winpsIsAvailable = False
    try:
        import winps
        winpsIsAvailable = True
    except ImportError:
        pass
# pylint: enable=import-error,wrong-import-position

import psutil

import rqd.compiled_proto.host_pb2
import rqd.compiled_proto.report_pb2
import rqd.rqconstants
import rqd.rqexceptions
import rqd.rqswap
import rqd.rqutil
if platform.system() == "Windows":
    import rqd.winutils


log = logging.getLogger(__name__)
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
        self.__gpusets = set()

        # A dictionary built from /proc/cpuinfo containing
        # { <physical id> : { <core_id> : set([<processor>, <processor>, ...]), ... }, ... }
        self.__threadid_by_cpuid_and_coreid = {}

        # A reverse mapping of the above.
        # { <processor> : (<physical id>, <core_id>), ... }
        self.__cpuid_and_coreid_by_threadid = {}

        if platform.system() == 'Linux':
            self.__vmstat = rqd.rqswap.VmStat()

        self.state = rqd.compiled_proto.host_pb2.UP

        self.__renderHost = rqd.compiled_proto.report_pb2.RenderHost()
        self.__initMachineTags()
        self.__initMachineStats()

        self.__bootReport = rqd.compiled_proto.report_pb2.BootReport()
        # pylint: disable=no-member
        self.__bootReport.core_info.CopyFrom(self.__coreInfo)
        # pylint: enable=no-member

        self.__hostReport = rqd.compiled_proto.report_pb2.HostReport()
        # pylint: disable=no-member
        self.__hostReport.core_info.CopyFrom(self.__coreInfo)
        # pylint: enable=no-member

        self.__pidHistory = {}

        self.setupGpu()
        self.setupTaskset()

    def isNimbySafeToRunJobs(self):
        """Returns False if nimby should be triggered due to resource limits"""
        if platform.system() == "Linux":
            self.updateMachineStats()
            # pylint: disable=no-member
            if self.__renderHost.free_mem < rqd.rqconstants.MINIMUM_MEM:
                return False
            if self.__renderHost.free_swap < rqd.rqconstants.MINIMUM_SWAP:
                return False
            # pylint: enable=no-member
        return True

    @rqd.rqutil.Memoize
    def isDesktop(self):
        """Returns True if machine starts in run level 5 (X11)
           by checking /etc/inittab. False if not."""
        if rqd.rqconstants.OVERRIDE_IS_DESKTOP:
            return True
        return False

    def isUserLoggedIn(self):
        """Returns whether a user is logged into the machine RQD is running on."""

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
                            log.warning('User %s logged into display :%s', cols[0], displayNum)
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

    def __updateGpuAndLlu(self, frame):
        if 'GPU_LIST' in frame.runFrame.attributes:
            usedGpuMemory = 0
            for unitId in frame.runFrame.attributes.get('GPU_LIST').split(','):
                usedGpuMemory += self.getGpuMemoryUsed(unitId)

            frame.usedGpuMemory = usedGpuMemory
            frame.maxUsedGpuMemory = max(usedGpuMemory, frame.maxUsedGpuMemory)

        if os.path.exists(frame.runFrame.log_dir_file):
            stat = os.stat(frame.runFrame.log_dir_file).st_mtime
            frame.lluTime = int(stat)

    def _getStatFields(self, pidFilePath):
        """ Read stats file and return list of values
        Stats file can star with these formats:
         - 105 name ...
         - 105 (name) ...
         - 105 (name with space) ...
         - 105 (name with) (space and parenthesis) ...
        """
        with open(pidFilePath, "r", encoding='utf-8') as statFile:
            txt = statFile.read()
            try:
                open_par_index = txt.index('(')
                close_par_index = txt.rindex(')')
                name = txt[open_par_index:close_par_index].strip("()")
                reminder = (txt[0:open_par_index] + txt[close_par_index + 1:]).split()
                return reminder[0:1] + [name] + reminder[1:]
            except ValueError:
                return txt.split()

    def rssUpdate(self, frames):
        """Updates the rss and maxrss for all running frames"""
        if platform.system() == 'Windows' and winpsIsAvailable:
            values = list(frames.values())
            pids = [frame.pid for frame in list(
                filter(lambda frame: frame.pid > 0, values)
            )]
            # pylint: disable=no-member
            stats = winps.update(pids)
            # pylint: enable=no-member
            for frame in values:
                self.__updateGpuAndLlu(frame)
                if frame.pid > 0 and frame.pid in stats:
                    stat = stats[frame.pid]
                    frame.rss = stat["rss"] // 1024
                    frame.maxRss = max(frame.rss, frame.maxRss)
                    frame.runFrame.attributes["pcpu"] = str(
                        stat["pcpu"] * self.__coreInfo.total_cores
                    )
            return

        if platform.system() != 'Linux':
            return

        pids = {}
        for pid in os.listdir("/proc"):
            if pid.isdigit():
                try:
                    statFields = self._getStatFields(rqd.rqconstants.PATH_PROC_PID_STAT
                                                     .format(pid))
                    pids[pid] = {
                        "pid": str(pid),
                        "name": statFields[1],
                        "state": statFields[2],
                        "parentid": statFields[3],
                        "pgrp": statFields[4],
                        "session": statFields[5],
                        # virtual memory size is in bytes convert to kb
                        "vsize": int(statFields[22]),
                        "rss": statFields[23],
                        # These are needed to compute the cpu used
                        "utime": statFields[13],
                        "stime": statFields[14],
                        "cutime": statFields[15],
                        "cstime": statFields[16],
                        # The time in jiffies the process started
                        # after system boot.
                        "start_time": statFields[21],
                        # Fetch swap usage
                        "swap": self._getProcSwap(pid),
                    }

                    # TODO: Improve this logic to avoid collecting data from all running procs.
                    # instead, focus on the monitored procs hierarchy
                    # cmdline:
                    p = psutil.Process(int(pid))
                    pids[pid]["cmd_line"] = p.cmdline()

                    # 2. Collect Statm file: /proc/[pid]/statm (same as status vsize in kb)
                    #    - size: "total program size"
                    #    - rss: inaccurate, similar to VmRss in /proc/[pid]/status
                    child_statm_fields = self._getStatFields(
                        rqd.rqconstants.PATH_PROC_PID_STATM.format(pid))
                    pids[pid]['statm_size'] = \
                        int(re.search(r"\d+", child_statm_fields[0]).group()) \
                        if re.search(r"\d+", child_statm_fields[0]) else -1
                    pids[pid]['statm_rss'] = \
                        int(re.search(r"\d+", child_statm_fields[1]).group()) \
                        if re.search(r"\d+", child_statm_fields[1]) else -1

                # pylint: disable=broad-except
                except (OSError, IOError, psutil.ZombieProcess):
                    # Many Linux processes are ephemeral and will disappear before we're able
                    # to read them. This is not typically indicative of a problem.
                    log.debug('Failed to read stat/statm file for pid %s', pid)

        # pylint: disable=too-many-nested-blocks
        try:
            now = int(time.time())
            pidData = {"time": now}
            bootTime = self.getBootTime()

            values = list(frames.values())
            for frame in values:
                pid = str(frame.pid)
                if pid is not None and frame.pid > 0 and pid in pids:
                    visited = [pid]
                    children = [pids[pid]]
                    self._collectChildren(pid, pids, visited, children)
                    rss = 0
                    vsize = 0
                    swap = 0
                    pcpu = 0
                    for data in children:
                        child_pid = data["pid"]
                        try:
                            rss += int(data["rss"])
                            vsize += int(data["vsize"])
                            swap += int(data["swap"])

                            # jiffies used by this process, last two means that dead
                            # children are counted
                            totalTime = int(data["utime"]) + \
                                        int(data["stime"]) + \
                                        int(data["cutime"]) + \
                                        int(data["cstime"])

                            # Seconds of process life, boot time is already in seconds
                            seconds = now - bootTime - \
                                      float(data["start_time"]) / rqd.rqconstants.SYS_HERTZ
                            if seconds:
                                if child_pid in self.__pidHistory:
                                    # Percent cpu using decaying average, 50% from 10 seconds
                                    # ago, 50% from last 10 seconds:
                                    oldTotalTime, oldSeconds, oldPidPcpu = \
                                        self.__pidHistory[child_pid]
                                    # checking if already updated data
                                    if seconds != oldSeconds:
                                        pidPcpu = ((totalTime - oldTotalTime) /
                                                   float(seconds - oldSeconds))
                                        pcpu += (oldPidPcpu + pidPcpu) / 2  # %cpu
                                        pidData[child_pid] = totalTime, seconds, pidPcpu
                                else:
                                    pidPcpu = totalTime / seconds
                                    pcpu += pidPcpu
                                    pidData[child_pid] = totalTime, seconds, pidPcpu

                            # These fields are not always present
                            _statm_rss = _statm_size = 0
                            try:
                                _statm_rss = int(data.get(["statm_rss"], 0))
                                _statm_size = int(data.get(["statm_size"], 0))
                            # pylint: disable=broad-except
                            except ValueError:
                                # Ignore these fields if they are not set on the proc file
                                pass

                            # If children was already accounted for, only keep the highest
                            # recorded rss value
                            if child_pid in frame.childrenProcs:
                                childRss = (int(data["rss"]) * resource.getpagesize()) // 1024
                                if childRss > frame.childrenProcs[child_pid]['rss']:
                                    frame.childrenProcs[child_pid]['rss_page'] = int(data["rss"])
                                    frame.childrenProcs[child_pid]['rss'] = childRss
                                    frame.childrenProcs[child_pid]['vsize'] = \
                                        int(data["vsize"]) // 1024
                                    frame.childrenProcs[child_pid]['swap'] = swap // 1024
                                    frame.childrenProcs[child_pid]['statm_rss'] = \
                                        _statm_rss * resource.getpagesize() // 1024
                                    frame.childrenProcs[child_pid]['statm_size'] = \
                                        _statm_size * resource.getpagesize() // 1024
                            else:
                                frame.childrenProcs[child_pid] = \
                                    {'name': data['name'],
                                     'rss_page': int(data["rss"]),
                                     'rss': (int(data["rss"]) * resource.getpagesize()) // 1024,
                                     'vsize': int(data["vsize"])  // 1024,
                                     'swap': swap // 1024,
                                     'state': data['state'],
                                     # statm reports in pages (~ 4kB)
                                     # same as VmRss in /proc/[child_pid]/status (in KB)
                                     'statm_rss': _statm_rss * resource.getpagesize() // 1024,
                                     'statm_size': _statm_size * resource.getpagesize() // 1024,
                                     'cmd_line': data.get("cmd_line", ""),
                                     'start_time': seconds}

                        # pylint: disable=broad-except
                        except Exception as e:
                            log.info(
                                'Failure with pid rss update due to: %s at %s',
                                e, traceback.extract_tb(sys.exc_info()[2]))
                    # convert bytes to KB
                    rss = (rss * resource.getpagesize()) // 1024
                    vsize = int(vsize/1024)
                    swap = swap // 1024

                    frame.rss = rss
                    frame.maxRss = max(rss, frame.maxRss)
                    frame.usedSwapMemory = swap

                    if os.path.exists(frame.runFrame.log_dir_file):
                        stat = os.stat(frame.runFrame.log_dir_file).st_mtime
                        frame.lluTime = int(stat)

                    frame.vsize = vsize
                    frame.maxVsize = max(vsize, frame.maxVsize)

                    frame.runFrame.attributes["pcpu"] = str(pcpu)

                    self.__updateGpuAndLlu(frame)

            # Store the current data for the next check
            self.__pidHistory = pidData

        # pylint: disable=broad-except
        except Exception as e:
            log.exception('Failure with rss update due to: %s', e)

    def _collectChildren(self, current_pid: str,
        all_pids: dict[str, dict[str, str]], visited: list[str],
        children: list[dict[str, str]]):
        """Recursive method to collect all children of first_parent_pid.

        The list of children is returned on the arg children"""
        for child_pid, data in all_pids.items():
            if data["parentid"] == current_pid and child_pid not in visited:
                children.append(data)
                visited.append(child_pid)
                self._collectChildren(child_pid, all_pids, visited, children)

    def _getProcSwap(self, pid):
        """Helper function to get swap memory used by a process"""
        swap_used = 0
        try:
            with open("/proc/%s/status" % pid, "r", encoding='utf-8') as statusFile:
                for line in statusFile:
                    if line.startswith("VmSwap:"):
                        swap_used = int(line.split()[1])
                        break
        except FileNotFoundError:
            log.info('Process %s terminated before swap info could be read.', pid)
        except Exception as e:
            log.warning('Failed to read swap usage for pid %s: %s', pid, e)
        return swap_used

    def getLoadAvg(self):
        """Returns average number of processes waiting to be served
           for the last 1 minute multiplied by 100."""
        if platform.system() == "Linux":
            with open(rqd.rqconstants.PATH_LOADAVG, "r", encoding='utf-8') as loadAvgFile:
                loadAvg = int(float(loadAvgFile.read().split()[0]) * 100)
                if self.__enabledHT():
                    loadAvg = loadAvg // self.getHyperthreadingMultiplier()
                loadAvg = loadAvg + rqd.rqconstants.LOAD_MODIFIER
                loadAvg = max(loadAvg, 0)
                return int(loadAvg)
        elif platform.system() == "Windows":
            # Use psutil to get the CPU utilization over 1 second
            # This is not the same as load average, but it gives a
            # similar idea of CPU load.
            loadAvg = psutil.cpu_percent(interval=1)
            return int(loadAvg * 100)
        return 0

    @rqd.rqutil.Memoize
    def getBootTime(self):
        """Returns epoch when the system last booted"""
        if os.path.isfile(rqd.rqconstants.PATH_STAT):
            with open(rqd.rqconstants.PATH_STAT, "r", encoding='utf-8') as statFile:
                for line in statFile:
                    if line.startswith("btime"):
                        return int(line.split()[1])
        return int(psutil.boot_time())

    @rqd.rqutil.Memoize
    def getGpuCount(self):
        """Returns the total gpu's on the machine"""
        return self.__getGpuValues()['count']

    @rqd.rqutil.Memoize
    def getGpuMemoryTotal(self):
        """Returns the total gpu memory in kb for CUE_GPU_MEMORY"""
        return self.__getGpuValues()['total']

    def getGpuMemoryFree(self):
        """Returns the available gpu memory in kb for CUE_GPU_MEMORY"""
        return self.__getGpuValues()['free']

    def getGpuMemoryUsed(self, unitId):
        """Returns the available gpu memory in kb for CUE_GPU_MEMORY"""
        usedMemory = self.__getGpuValues()['used']
        return usedMemory[unitId] if unitId in usedMemory else 0

    # pylint: disable=attribute-defined-outside-init
    def __resetGpuResults(self):
        self.gpuResults = {'count': 0, 'total': 0, 'free': 0, 'used': {}, 'updated': 0}

    def __getGpuValues(self):
        if not hasattr(self, 'gpuNotSupported'):
            if not hasattr(self, 'gpuResults'):
                self.__resetGpuResults()
            if not rqd.rqconstants.ALLOW_GPU:
                self.gpuNotSupported = True
                return self.gpuResults
            if self.gpuResults['updated'] > int(time.time()) - 60:
                return self.gpuResults
            try:
                nvidia_smi = subprocess.getoutput(
                    'nvidia-smi --query-gpu=memory.total,memory.free,count'
                    ' --format=csv,noheader')
                total = 0
                free = 0
                count = 0
                unitId = 0
                for line in nvidia_smi.splitlines():
                    # Example "16130 MiB, 16103 MiB, 8"
                    # 1 MiB = 1048.576 KB
                    l = line.split()
                    unitTotal = math.ceil(int(l[0]) * 1048.576)
                    unitFree = math.ceil(int(l[2]) * 1048.576)
                    total += unitTotal
                    free += unitFree
                    count = int(l[-1])
                    self.gpuResults['used'][str(unitId)] = unitTotal - unitFree
                    unitId += 1

                self.gpuResults['total'] = int(total)
                self.gpuResults['free'] = int(free)
                self.gpuResults['count'] = count
                self.gpuResults['updated'] = int(time.time())
            # pylint: disable=broad-except
            except Exception as e:
                self.gpuNotSupported = True
                self.__resetGpuResults()
                log.warning(
                    'Failed to query nvidia-smi due to: %s at %s',
                    e, traceback.extract_tb(sys.exc_info()[2]))
        else:
            self.__resetGpuResults()
        return self.gpuResults

    def __getSwapout(self):
        if platform.system() == "Linux":
            try:
                return str(int(self.__vmstat.getRecentPgoutRate()))
            # pylint: disable=broad-except
            except Exception:
                return str(0)
        return str(0)

    @rqd.rqutil.Memoize
    def getTimezone(self):
        """Returns the desired timezone"""
        if time.tzname[0] == 'IST':
            return 'IST'
        return 'PST8PDT'

    @rqd.rqutil.Memoize
    def getHostname(self):
        """Returns the machine's fully qualified domain name"""
        return rqd.rqutil.getHostname()

    @rqd.rqutil.Memoize
    def getPathEnv(self):
        """Returns the correct path environment for the given machine"""
        if rqd.rqconstants.RQD_USE_PATH_ENV_VAR:
            return os.getenv('PATH')
        if platform.system() == 'Linux':
            return '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'
        if platform.system() == 'Windows':
            return 'C:/Windows/system32;C:/Windows;C:/Windows/System32/Wbem'
        return ''

    @rqd.rqutil.Memoize
    def getTempPath(self):
        """Returns the correct mcp path for the given machine"""
        if os.path.isdir("/mcp/"):
            return "/mcp/"
        return '%s/' % tempfile.gettempdir()

    def reboot(self):
        """Reboots the machine immediately"""
        if platform.system() == "Linux":
            log.warning("Rebooting machine")
            # pylint: disable=consider-using-with
            subprocess.Popen(['/usr/bin/sudo', '/sbin/reboot', '-f'])

    # pylint: disable=no-member
    def __initMachineTags(self):
        """Sets the hosts tags"""
        self.__renderHost.tags.append("rqdv-%s" % rqd.rqconstants.VERSION)

        if rqd.rqconstants.RQD_TAGS:
            for tag in rqd.rqconstants.RQD_TAGS.split():
                self.__renderHost.tags.append(tag)

        # Tag with desktop if it is a desktop
        if self.isDesktop():
            self.__renderHost.tags.append("desktop")

        if platform.system() == 'Windows':
            self.__renderHost.tags.append("windows")
            return

        if platform.uname()[-1] in ("i386", "i686"):
            self.__renderHost.tags.append("32bit")
        elif platform.uname()[-1] == "x86_64":
            self.__renderHost.tags.append("64bit")
        self.__renderHost.tags.append(platform.uname()[2].replace(".EL.spi", "").replace("smp", ""))

    def testInitMachineStats(self, pathCpuInfo):
        """Initializes machine stats outside of normal startup process. Used for testing."""
        self.__initMachineStats(pathCpuInfo=pathCpuInfo)
        return self.__renderHost, self.__coreInfo

    def __initMachineStats(self, pathCpuInfo=None):
        """Updates static machine information during initialization

        @type  pathCpuInfo: str
        @param pathCpuInfo: Path to a specific cpuinfo file
        """
        self.__renderHost.name = self.getHostname()
        self.__renderHost.boot_time = self.getBootTime()
        self.__renderHost.facility = rqd.rqconstants.DEFAULT_FACILITY
        self.__renderHost.attributes['SP_OS'] = rqd.rqconstants.SP_OS

        # Get the total memory and swap
        self.updateMachineStats()

        # By default all systems will just have one proc/core
        cpu_count = total_cores = total_threads = core_per_proc = thread_per_proc = 1

        if platform.system() == "Linux" or pathCpuInfo is not None:
            self.__initStatsLinux(pathCpuInfo)
            (cpu_count, total_cores, total_threads,
             core_per_proc, thread_per_proc) = self.count_cores()
        elif platform.system() == 'Windows':
            self.__initStatsWindows()
            (cpu_count, total_cores, total_threads,
             core_per_proc, thread_per_proc) = self.count_cores()

        # Override values from rqd.conf
        if rqd.rqconstants.OVERRIDE_MEMORY is not None:
            log.warning("Manually overriding the total memory")
            self.__renderHost.total_mem = rqd.rqconstants.OVERRIDE_MEMORY

        if rqd.rqconstants.OVERRIDE_PROCS is not None:
            log.warning("Manually overriding the number of reported procs")
            cpu_count = rqd.rqconstants.OVERRIDE_PROCS

        if rqd.rqconstants.OVERRIDE_CORES is not None:
            log.warning("Manually overriding the number of reported cores")
            core_per_proc = rqd.rqconstants.OVERRIDE_CORES
            total_cores = core_per_proc * cpu_count
            if rqd.rqconstants.OVERRIDE_THREADS is None:
                thread_per_proc = core_per_proc
                total_threads = total_cores

        if rqd.rqconstants.OVERRIDE_THREADS is not None:
            log.warning("Manually overriding the number of reported threads")
            thread_per_proc = rqd.rqconstants.OVERRIDE_THREADS
            total_threads = thread_per_proc * cpu_count
            if rqd.rqconstants.OVERRIDE_CORES is None:
                core_per_proc = thread_per_proc
                total_cores = total_threads

        self.__coreInfo.idle_cores = total_cores * rqd.rqconstants.CORE_VALUE
        # TODO: add idle_threads ? anyway we need to address reserving threads instead of cores.
        self.__coreInfo.total_cores = total_cores * rqd.rqconstants.CORE_VALUE
        self.__coreInfo.total_threads = total_threads * rqd.rqconstants.CORE_VALUE
        self.__renderHost.num_procs = cpu_count
        self.__renderHost.cores_per_proc = core_per_proc * rqd.rqconstants.CORE_VALUE
        self.__renderHost.threads_per_proc = thread_per_proc * rqd.rqconstants.CORE_VALUE

        ht_multiplier = thread_per_proc / core_per_proc
        if ht_multiplier >= 1:
            self.__renderHost.attributes['hyperthreadingMultiplier'] = str(ht_multiplier)

    def count_cores(self):
        """Counts the number of cores on the machine"""
        cpu_count = len(self.__threadid_by_cpuid_and_coreid.keys())
        total_threads = len(self.__cpuid_and_coreid_by_threadid.keys())
        thread_per_proc = total_threads // cpu_count
        total_cores = sum(
            len(cores) for _, cores in self.__threadid_by_cpuid_and_coreid.items()
        )
        core_per_proc = total_cores // cpu_count

        return cpu_count, total_cores, total_threads, core_per_proc, thread_per_proc

    def __initStatsLinux(self, pathCpuInfo=None):
        """Init machine stats for Linux platforms.

        @type  pathCpuInfo: str
        @param pathCpuInfo: Path to a specific cpuinfo file
        """
        coreInfo = []
        # Reads static information from /proc/cpuinfo
        with (open(pathCpuInfo or rqd.rqconstants.PATH_CPUINFO, "r",
                   encoding='utf-8') as cpuinfoFile):
            infoBlock = {} # Gets reset for each processor block
            for line in cpuinfoFile:
                lineList = line.strip().replace("\t", "").split(": ")
                # A normal entry added to the singleCore dictionary
                if len(lineList) >= 2:
                    infoBlock[lineList[0]] = lineList[1]
                # An entry without data
                elif len(lineList) == 1:
                    infoBlock[lineList[0]] = ""
                # The end of a processor block
                if lineList == ['']:
                    # Get relevant information from the block
                    logical_core_id = infoBlock['processor']
                    cpu_id = infoBlock.get('physical id', infoBlock['processor'])
                    physical_core_id = infoBlock.get('core id', infoBlock['processor'])
                    # Save that and iterate
                    coreInfo.append((cpu_id, physical_core_id, logical_core_id))
                    infoBlock.clear()

        self.__updateProcsMappings(coreInfo=coreInfo)

    def __initStatsWindows(self):
        """Init machine stats for Windows platforms.
        """
        coreInfo = rqd.rqwinutils.get_logical_processor_information_ex()
        self.__updateProcsMappings(coreInfo=coreInfo)

    def __updateProcsMappings(self, coreInfo):
        """
        Update `__threadid_by_cpuid_and_coreid` and `__cpuid_and_coreid_by_threadid` mappings.

        @type  coreInfo: list[tuple[str, str, str]]
        @param coreInfo: A list of tuples containing CPU ID, Physical Core ID, and Logical Core ID.

        Implementation detail:
        One CPU has one or more physical cores,
         and each physical core has one or more logical cores.
        Some CPUs have hyper-threading, which means that each logical core is treated as
         a separate core by the operating system, while being on the same physical core.
        Hybrid CPUs have performance cores that are hyper-threaded,
         and efficient cores that are mono-threaded.
        On Windows, we can't detect each physical CPU,
         so instead we use CPU groups (64 cores per group).
        """

        # Reset mappings
        self.__threadid_by_cpuid_and_coreid = {}
        self.__cpuid_and_coreid_by_threadid = {}

        for (cpu_id, physical_core_id, logical_core_id) in coreInfo:
            self.__threadid_by_cpuid_and_coreid.setdefault(
                str(cpu_id), {}).setdefault(
                physical_core_id, set()).add(str(logical_core_id))
            self.__cpuid_and_coreid_by_threadid[logical_core_id] = (str(cpu_id),
                                                                    str(physical_core_id))

    def updateWindowsMemory(self):
        """Updates the internal store of memory available for Windows."""
        if not hasattr(self, '__windowsStat'):
            self.__windowsStat = rqd.rqwinutils.MEMORYSTATUSEX()
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(self.__windowsStat))

        stat = self.__windowsStat
        temp_path = os.getenv('TEMP')  # Windows temp directory
        disk_usage = psutil.disk_usage(temp_path)

        self.__renderHost.total_mcp = disk_usage.total // 1024
        self.__renderHost.free_mcp = disk_usage.free // 1024

        self.__renderHost.total_mem = int(stat.ullTotalPhys / 1024)
        self.__renderHost.free_mem = int(stat.ullAvailPhys / 1024)

        self.__renderHost.total_swap = int(stat.ullTotalPageFile / 1024)
        self.__renderHost.free_swap = int(stat.ullAvailPageFile / 1024)

        self.__renderHost.num_gpus = self.getGpuCount()
        self.__renderHost.total_gpu_mem = self.getGpuMemoryTotal()
        self.__renderHost.free_gpu_mem = self.getGpuMemoryFree()

    def updateLinuxMemory(self):
        """Gets information on system memory for Linux."""
        # Reads dynamic information for mcp
        mcpStat = os.statvfs(self.getTempPath())
        self.__renderHost.free_mcp = (mcpStat.f_bavail * mcpStat.f_bsize) // KILOBYTE

        # Reads dynamic information from /proc/meminfo
        with open(rqd.rqconstants.PATH_MEMINFO, "r", encoding='utf-8') as fp:
            for line in fp:
                if line.startswith("MemFree"):
                    freeMem = int(line.split()[1])
                elif line.startswith("SwapFree"):
                    freeSwapMem = int(line.split()[1])
                elif line.startswith("SwapTotal"):
                    self.__renderHost.total_swap = int(line.split()[1])
                elif line.startswith("Cached"):
                    cachedMem = int(line.split()[1])
                elif line.startswith("MemTotal"):
                    self.__renderHost.total_mem = int(line.split()[1])

        self.__renderHost.free_swap = freeSwapMem
        self.__renderHost.free_mem = freeMem + cachedMem
        self.__renderHost.num_gpus = self.getGpuCount()
        self.__renderHost.total_gpu_mem = self.getGpuMemoryTotal()
        self.__renderHost.free_gpu_mem = self.getGpuMemoryFree()

        self.__renderHost.attributes['swapout'] = self.__getSwapout()

    def updateMacMemory(self):
        """Updates the internal store of memory available, macOS compatible version."""
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
            self.updateLinuxMemory()

        elif platform.system() == 'Darwin':
            self.updateMacMemory()

        elif platform.system() == 'Windows':
            self.updateWindowsMemory()

        # Updates dynamic information
        self.__renderHost.load = self.getLoadAvg()
        self.__renderHost.nimby_enabled = self.__rqCore.nimby.is_ready
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
        self.__rqCore.sanitizeFrames()
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

    def getHyperthreadingMultiplier(self):
        """
        Multiplier used to compute the number of threads that can be allocated simultaneously
        on a core. This is a float as it can be fractional for hybrid cores.
        """
        return float(self.__renderHost.attributes.get('hyperthreadingMultiplier', 1.0))

    def setupTaskset(self):
        """ Setup rqd for hyper-threading """
        self.__coreInfo.reserved_cores.clear()

    def setupGpu(self):
        """ Setup rqd for Gpus """
        self.__gpusets = set(range(self.getGpuCount()))

    def reserveCores(self, coresCount=0, logical=True):
        """ Reserve cores for use by taskset
        taskset -c 0,1,8,9 COMMAND
        Not thread save, use with locking.
        @type   coresCount: int
        @param  coresCount: The total physical cores reserved by the frame.
        @type   logical: bool
        @param  logical: If True, reserve logical cores (aka threads), else physical cores.
        note: logical cores is what you see in htop or task manager.
        @rtype:  string
        @return: The cpu-list for taskset -c
        """

        if coresCount % 100:
            log.warning('Taskset: Can not reserveHT with fractional cores')
            return None
        log.info('Taskset: Requesting reserve of %d', (coresCount // 100))

        # Look for the most idle physical cpu.
        # Prefer to assign cores from the same physical cpu.
        # Spread different frames around on different physical cpus.
        avail_cores = {}
        avail_procs_count = 0
        reserved_cores = self.__coreInfo.reserved_cores

        for physid, cores in self.__threadid_by_cpuid_and_coreid.items():
            for coreid in cores.keys():
                if int(physid) in reserved_cores and \
                        int(coreid) in reserved_cores[int(physid)].coreid:
                    continue
                avail_cores.setdefault(physid, set()).add(coreid)
                if logical:
                    # Count all threads (logical cores)
                    avail_procs_count += len(cores[coreid])
                else:
                    # Count only physical cores
                    avail_procs_count += 1

        query_procs = coresCount / 100

        if avail_procs_count < query_procs:
            err = ('Not launching, insufficient cores to reserve '
                   'based on coresCount (%s < %s)')  \
                  % (avail_procs_count, query_procs)
            log.critical(err)
            raise rqd.rqexceptions.CoreReservationFailureException(err)

        tasksets = []

        for physid, cores in sorted(
                avail_cores.items(),
                # Return the physical socket that has
                # the most idle cores first.
                key=lambda tup: len(tup[1]),
                reverse=True):
            cores = sorted(list(cores), key=int)
            while query_procs > 0 and len(cores) > 0:
                # Reserve hyper-threaded cores first (2 threads(logical cores) for 1 physical core)
                # Avoid booking a hyper-threaded core for an odd thread count remainder
                # ex: if query_procs==2, get the next core with 2 threads
                # ex: if query_procs==1, get the next core with 1 thread or any other core
                # here we fall back on the first physical core
                # (assuming "first in list" == "has more threads")
                # if we didn't find a core with the right number of threads, and continue the loop.
                coreid = next(iter(
                    [cid for cid in cores
                     if len(self.__threadid_by_cpuid_and_coreid[physid][cid]) <= query_procs]),
                    cores[0])
                cores.remove(coreid)
                procids = self.__threadid_by_cpuid_and_coreid[physid][coreid]
                reserved_cores[int(physid)].coreid.extend([int(coreid)])
                if logical:
                    query_procs -= len(procids)
                else:
                    query_procs -= 1
                tasksets.extend(procids)

            if query_procs <= 0:
                # Could be negative if we reserved a full core with more threads than needed
                break

        log.warning('Taskset: Reserving procs - %s', ','.join(tasksets))

        return ','.join(tasksets)


    def reserveHT(self, frameCores):
        """ Reserve cores for use by taskset
        taskset -c 0,1,8,9 COMMAND
        Not thread save, use with locking.
        @type   frameCores: int
        @param  frameCores: The total physical cores reserved by the frame.
        @rtype:  string
        @return: The cpu-list for taskset -c
        """
        warnings.warn(
            "The `reserveHT` method is deprecated and will be removed in a future release. "
            "Use `reserveCores(logical=False)` instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return self.reserveCores(frameCores, logical=False)

    # pylint: disable=inconsistent-return-statements
    def releaseHT(self, reservedHT):
        """ Release cores used by taskset
        Format: 0,1,8,9
        Not thread safe, use with locking.
        @type:  string
        @param: The cpu-list used for taskset to release. ex: '0,8,1,9'
        """

        log.debug('Taskset: Releasing cores - %s', reservedHT)

        # Remove these cores from the reserved set.
        # Silently ignore any that weren't really reserved or
        # aren't valid core identities.
        reserved_cores = self.__coreInfo.reserved_cores
        for core in reservedHT.split(','):
            physical_id_str, core_id_str = self.__cpuid_and_coreid_by_threadid.get(core)
            physical_id = int(physical_id_str)
            core_id = int(core_id_str)

            if physical_id in reserved_cores and core_id in reserved_cores[physical_id].coreid:
                reserved_cores[physical_id].coreid.remove(core_id)
                if len(reserved_cores[physical_id].coreid) == 0:
                    del reserved_cores[physical_id]

    def reserveGpus(self, reservedGpus):
        """ Reserve gpus
        @type   reservedGpus: int
        @param  reservedGpus: The total gpus reserved by the frame.
        @rtype:  string
        @return: The gpu-list. ex: '0,1,8,9'
        """
        if len(self.__gpusets) < reservedGpus:
            err = 'Not launching, insufficient GPUs to reserve based on reservedGpus'
            log.critical(err)
            raise rqd.rqexceptions.CoreReservationFailureException(err)

        gpusets = []
        for _ in range(reservedGpus):
            gpu = self.__gpusets.pop()
            gpusets.append(str(gpu))

        return ','.join(gpusets)

    def releaseGpus(self, reservedGpus):
        """ Release gpus
        @type:  string
        @param: The gpu-list to release. ex: '0,1,8,9'
        """
        log.debug('GPU set: Releasing gpu - %s', reservedGpus)
        for gpu in reservedGpus.split(','):
            if int(gpu) < self.getGpuCount():
                self.__gpusets.add(int(gpu))
