#!/bin/sh


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




""":"
if [ -x /usr/local/bin/python ];then
    exec /usr/local/bin/python $0 ${1+"$@"}
elif [ -x /opt/local/bin/python2.4 ];then
    exec /opt/local/bin/python2.4 $0 ${1+"$@"}
elif [ -x /usr/bin/python2.3 ];then
    echo "WARNING, python 2.3 may not support everything rqd uses"
    exec /usr/bin/python2.3 $0 ${1+"$@"}
else
    echo "$0: Unable to find python" >&2
    exit 2
fi
"""

# $Id$
#
# A simple test script that acts like the cuebot by listening for messages from RQD.
#
# Author: John Welborn (jwelborn@imageworks.com)

import thread
import time
import os
import sys

libPath = "%s/../" % os.path.dirname(__file__)
sys.path.append(libPath)

from rqconstants import STRING_TO_CUEBOT, CUEBOT_PORT
import rqutil

import python_ice_server.loader
python_ice_server.loader.setup_python_for_ice_3_3()

import Ice
Ice.loadSlice('--all -I%s/slice/spi -I%s/slice/cue %s/slice/cue/cue_ice.ice' % (libPath, libPath, libPath))
import cue.CueIce as CueIce

# THIS IS FOR TESTING rqd.py ONLY

class RqdReportStatic(CueIce.RqdReportStatic):
    """Test class implements RqdReportStatic interface.
       Recieved reports are stored in the variables listed below.
       Create as an object to connect.
       call .wait() to block until ice exits.
       call .stop to destory the ice communicator, after .wait() will exit."""
    lastReportRqdStartup = None
    lastReportStatus = None
    lastReportRunningFrameCompletion = None

    statusCheckin = {}

    start = False

    def __init__(self, stringToCuebot=STRING_TO_CUEBOT, cuebotPort=CUEBOT_PORT):
        self.verbose = 2

        # This causes the connection to close after 1 second
        initData = Ice.InitializationData()
        props = initData.properties = Ice.createProperties()
        props.setProperty('Ice.ACM.Server', '1')

        self.communicator = Ice.initialize(initData)
        print "cuebotPort = %s, stringToCuebot = %s, pid = %d" % (cuebotPort, stringToCuebot, os.getpid())
        self.DataFromRQD = self.communicator.createObjectAdapterWithEndpoints(stringToCuebot, 'default -p ' + cuebotPort)
        self.DataFromRQD.add(self, self.communicator.stringToIdentity(STRING_TO_CUEBOT))
        self.DataFromRQD.activate()
        print "Cuebot Listener started"
        self.start = True

    def wait(self):
        try:
            self.communicator.waitForShutdown()
        except KeyboardInterrupt:
            print "Killed by keyboard interrupt, RqdReportStatic exiting"
        self.communicator.destroy()
        self.start = False

    def stop(self):
        self.communicator.destroy()

    def _trackUpdateTime(self, report):
        now = time.time()
        self.statusCheckin[report.host.name] = {"last": now, "report": report}
        print "-"*20, time.asctime(time.localtime(now)), "-"*20
        for host in sorted(self.statusCheckin.keys()):
            secondsSinceLast = now - self.statusCheckin[host]["last"]
            if host == report.host.name:
               print " >",
            else:
               print "  ",
            print host.ljust(15) \
                  , str(int(secondsSinceLast)).ljust(10) \
                  , str(self.statusCheckin[host]["report"].host.load).ljust(5) \
                  , str(self.statusCheckin[host]["report"].host.freeMem).ljust(10) \
                  , ",".join(self.statusCheckin[host]["report"].host.tags)

    # These are defined by the rqd_ice.ice slice file:

    def reportRqdStartup(self, report, current=None):
        self.lastReportRqdStartup = report

        if self.verbose == 0:
            pass
        elif self.verbose == 1:
            sys.stdout.write("1")
            sys.stdout.flush()
        elif self.verbose == 2:
            print "%s : startup.host    - nimbyEnabled = %s, numProcs = %s, coresPerProc = %d, load = %s, bootTime = %s" % (report.host.name, report.host.nimbyEnabled, report.host.numProcs, report.host.coresPerProc, report.host.load,report.host.bootTime)
            print "%s : startup.host    - totalSwap = %s, totalMem = %s, totalMcp = %s, freeSwap = %s, freeMem = %s, freeMcp = %s" % (report.host.name, report.host.totalSwap, report.host.totalMem, report.host.totalMcp, report.host.freeSwap, report.host.freeMem, report.host.freeMcp)
            print "%s : startup.host    - tags = %s, state = %s" % (report.host.name, report.host.tags, report.host.state)
            print "%s : startup.coreInfo - totalCores = %s, idleCores = %s, lockedCores = %s, bookedCores = %s" % (report.host.name, report.coreInfo.totalCores, report.coreInfo.idleCores, report.coreInfo.lockedCores, report.coreInfo.bookedCores)
        elif self.verbose == 3:
            print "Receiving reportRqdStartup"
            print report
        elif self.verbose == 4:
            self._trackUpdateTime(report)

    def reportStatus(self, report, current=None):
        self.lastReportStatus = report

        if self.verbose == 0:
            pass
        elif self.verbose == 1:
            sys.stdout.write(".")
            sys.stdout.flush()
        elif self.verbose == 2:
            print "%s : status.host    - nimbyEnabled = %s, numProcs = %s, coresPerProc = %d, load = %s, bootTime = %s" % (report.host.name, report.host.nimbyEnabled, report.host.numProcs, report.host.coresPerProc, report.host.load,report.host.bootTime)
            print "%s : status.host    - totalSwap = %s, totalMem = %s, totalMcp = %s, freeSwap = %s, freeMem = %s, freeMcp = %s" % (report.host.name, report.host.totalSwap, report.host.totalMem, report.host.totalMcp, report.host.freeSwap, report.host.freeMem, report.host.freeMcp)
            print "%s : status.host    - tags = %s, state = %s" % (report.host.name, report.host.tags, report.host.state)
            for job in report.frames:
                print "%s : status.frames[x] - frameId = %s, jobId = %s, numCores = %d, usedMem = %s" % (report.host.name, job.frameId, job.jobId, job.numCores, job.usedMem)
            print "%s : status.coreInfo - totalCores = %s, idleCores = %s, lockedCores = %s, bookedCores = %s" % (report.host.name, report.coreInfo.totalCores, report.coreInfo.idleCores, report.coreInfo.lockedCores, report.coreInfo.bookedCores)
        elif self.verbose == 3:
            print "Receiving reportStatus"
            print report
        elif self.verbose == 4:
            self._trackUpdateTime(report)

    def reportRunningFrameCompletion(self, report, current=None):
        self.lastReportRunningFrameCompletion = report

        if self.verbose == 0:
            pass
        elif self.verbose == 1:
            sys.stdout.write("X")
            sys.stdout.flush()
        elif self.verbose == 2:
            print "%s : FrameCompletion.host    - nimbyEnabled = %s, numProcs = %s, coresPerProc = %d, load = %s, bootTime = %s" % (report.host.name, report.host.nimbyEnabled, report.host.numProcs, report.host.coresPerProc, report.host.load,report.host.bootTime)
            print "%s : FrameCompletion.host    - totalSwap = %s, totalMem = %s, totalMcp = %s, freeSwap = %s, freeMem = %s, freeMcp = %s" % (report.host.name, report.host.totalSwap, report.host.totalMem, report.host.totalMcp, report.host.freeSwap, report.host.freeMem, report.host.freeMcp)
            print "%s : FrameCompletion.host    - tags = %s" % (report.host.name, report.host.tags)
            print "%s : FrameCompletion.frame   - jobId = %s, frameId = %s, numCores = %d, usedMem = %d" % (report.host.name, report.frame.jobId, report.frame.frameId, report.frame.numCores, report.frame.usedMem)
            print "%s : FrameCompletion         - exitStatus = %s, exitSignal = %s, runTime = %s, maxRss = %s" % (report.host.name, report.exitStatus, report.exitSignal, report.runTime, report.maxRss)
        elif self.verbose == 3:
            print "Receiving reportRunningFrameCompletion"
            print report

if __name__ == "__main__":
    listener = RqdReportStatic(STRING_TO_CUEBOT, CUEBOT_PORT)
    listener.verbose = 2
    listener.wait()

