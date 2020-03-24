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


"""SYNOPSIS
     cuerqd [hostname] [OPTIONS]
      [hostname]            => RQD hostname (defaults to localhost)
      -s or --status        => Print RQD status
      -v or --version       => Print RQD version
      --lock <cores>        => Lock the specified cores
      --unlock <cores>      => Unlock the specified cores
      --lock all            => Lock all cores for the specified host
      --unlock all          => Unlock all cores for the specified host
      --nimby on            => Turn on 'Not in my back yard' (NIMBY) to stop processing on the specified host
      --nimby off           => Turn off 'Not in my back yard' (NIMBY) to start processing on the specified host
      --exit                => Lock host, wait until machine is idle and then shutdown RQD *
      --exit now            => KILL ALL running frames and shutdown RQD
      --restart             => Lock host, wait until machine is idle and then restart RQD *
      --restart now         => KILL ALL running frames and restart RQD
      --reboot              => Lock host, wait until machine is idle and then REBOOT machine *
      --reboot now          => KILL ALL running frames and REBOOT machine
    print
      --kill <frameid>      => Attempts to kill the given frame via its ICE proxy
      --getproxy <frameid>  => Returns the proxy for the given frameid (debug)
    print
     * Any unlock command will cancel this request
\n FOR TESTING:
      --test edu_frame        => Launch a test edu frame on an idle core
                                Use first core if none are available
      --test script_frame     => Same as above but launches a 5 second python script
      --test script_frame_mac => Same as above but for mac host
\nDESCRIPTION
      Displays information from or sends a command to an RQD host"""


from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from builtins import str
from builtins import object
import os
import sys
import argparse
import re
import random
import logging as log

import grpc

import rqd.compiled_proto.rqd_pb2
import rqd.compiled_proto.rqd_pb2_grpc
import rqd.rqconstants


class RqdHost(object):
    def __init__(self, rqdHost, rqdPort=rqd.rqconstants.RQD_GRPC_PORT):
        self.rqdHost = rqdHost
        self.rqdPort = rqdPort

        channel = grpc.insecure_channel('%s:%s' % (self.rqdHost, self.rqdPort))
        self.stub = rqd.compiled_proto.rqd_pb2_grpc.RqdInterfaceStub(channel)
        self.frameStub = rqd.compiled_proto.rqd_pb2_grpc.RunningFrameStub(channel)

    def status(self):
        return self.stub.ReportStatus(rqd.compiled_proto.rqd_pb2.RqdStaticReportStatusRequest())

    def getRunningFrame(self, frameId):
        return self.stub.GetRunFrame(
            rqd.compiled_proto.rqd_pb2.RqdStaticGetRunFrameRequest(frame_id=frameId))

    def nimbyOff(self):
        print(self.rqdHost, "Turning off Nimby")
        log.info("rqd nimbyoff by {0}".format(os.environ.get("USER")))
        self.stub.NimbyOff(rqd.compiled_proto.rqd_pb2.RqdStaticNimbyOffRequest())

    def nimbyOn(self):
        print(self.rqdHost, "Turning on Nimby")
        log.info("rqd nimbyon by {0}".format(os.environ.get("USER")))
        self.stub.NimbyOn(rqd.compiled_proto.rqd_pb2.RqdStaticNimbyOnRequest())

    def lockAll(self):
        print(self.rqdHost,"Locking all cores")
        self.stub.LockAll(rqd.compiled_proto.rqd_pb2.RqdStaticLockAllRequest())

    def unlockAll(self):
        print(self.rqdHost,"Unlocking all cores")
        self.stub.UnlockAll(rqd.compiled_proto.rqd_pb2.RqdStaticUnlockAllRequest())

    def lock(self, cores):
        cores = int(cores)
        print(self.rqdHost,"Locking %d cores" % cores)
        self.stub.Lock(rqd.compiled_proto.rqd_pb2.RqdStaticLockRequest(cores=cores))

    def unlock(self, cores):
        cores = int(cores)
        print(self.rqdHost,"Unlocking %d cores" % cores)
        self.stub.Unlock(rqd.compiled_proto.rqd_pb2.RqdStaticUnlockRequest(cores=cores))

    def shutdownRqdIdle(self):
        print(self.rqdHost,"Sending shutdownRqdIdle command")
        self.stub.ShutdownRqdIdle(rqd.compiled_proto.rqd_pb2.RqdStaticShutdownIdleRequest())

    def shutdownRqdNow(self):
        print(self.rqdHost,"Sending shutdownRqdNow command")
        self.stub.ShutdownRqdNow(rqd.compiled_proto.rqd_pb2.RqdStaticShutdownNowRequest())

    def restartRqdIdle(self):
        print(self.rqdHost,"Sending restartRqdIdle command")
        self.stub.RestartRqdIdle(rqd.compiled_proto.rqd_pb2.RqdStaticRestartIdleRequest())

    def restartRqdNow(self):
        print(self.rqdHost,"Sending restartRqdNow command")
        self.stub.RestartRqdNow(rqd.compiled_proto.rqd_pb2.RqdStaticRestartNowRequest())

    def rebootIdle(self):
        print(self.rqdHost,"Sending rebootIdle command")
        self.stub.RebootIdle(rqd.compiled_proto.rqd_pb2.RqdStaticRebootIdleRequest())

    def rebootNow(self):
        print(self.rqdHost,"Sending rebootNow command")
        self.stub.RebootNow(rqd.compiled_proto.rqd_pb2.RqdStaticRebootNowRequest())

    def launchFrame(self, frame):
        self.stub.LaunchFrame(rqd.compiled_proto.rqd_pb2.RqdStaticLaunchFrameRequest(run_frame=frame))

    def killFrame(self, frameId, message):
        runFrame = self.getRunningFrame(frameId)
        self.frameStub.Kill(run_frame=runFrame, message=message)


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument('host', nargs='?', default='localhost')
    parser.add_argument('-s', '--status', action='store_true')
    parser.add_argument('-v', '--version', action='store_true')
    parser.add_argument('--nimby', metavar='action', choices=['ON','OFF'])
    parser.add_argument('--lock', metavar='coreID', nargs='+')
    parser.add_argument('--unlock', metavar='coreID', nargs='+')
    parser.add_argument('--exit', nargs='?', const='wait')
    parser.add_argument('--restart', nargs='?', const='wait')
    parser.add_argument('--reboot', nargs='?', const='wait')
    parser.add_argument('--kill', metavar='frameID', nargs='+')
    parser.add_argument('--getproxy', metavar='frameID', nargs='+')
    parser.add_argument('--test', choices=['edu_frame','script_frame','script_frame_mac'])
     
    args = parser.parse_args()

    rqdHost = RqdHost(args.host)

    if args.status:
        print(rqdHost.status())
    if args.version:
        tagPrefix = 'rqdv-'
        for tag in rqdHost.status().host.tags:
            if tag.startswith(tagPrefix):
                print("version =", tag[len(tagPrefix):])
    if args.nimby == 'off':
        rqdHost.nimbyOff()
    elif args.nimby == 'on':
        rqdHost.nimbyOn()
    for arg in args.lock:
        if arg == 'all':
            rqdHost.lockAll()
        else:
            rqdHost.lock(arg)
    for arg in args.unlock:
        if arg == 'all':
            rqdHost.unlockAll()
        else:
            rqdHost.unlock(arg)
    if args.exit == 'now':
        rqdHost.shutdownRqdNow()
    elif args.exit == 'wait':
        rqdHost.shutdownRqdIdle()
    if args.restart == 'now':
        rqdHost.restartRqdNow()
    elif args.restart == 'wait':
        rqdHost.restartRqdIdle()
    if args.reboot == 'now':
        rqdHost.rebootNow()
    elif args.reboot == 'now':
        rqdHost.rebootIdle()
    for arg in args.kill:
        rqdHost.killFrame(arg, "Killed by %s using cuerqd.py" % os.environ.get("USER"))
    for arg in args.getproxy:
        frameProxy = rqdHost.getRunningFrame(arg)
        print(frameProxy)
    
    if args.test == 'edu_frame':
        print("Launching edu test frame (logs to /mcp)")
        frameNum = "0001"
        runFrame = rqd.compiled_proto.rqd_pb2.RunFrame()
        runFrame.job_id = "SD6F3S72DJ26236KFS"
        runFrame.job_name = "edu-trn_jwelborn-jwelborn_teapot_bty"
        runFrame.frame_id = "FD1S3I154O646UGSNN%s" % frameNum
        runFrame.frame_name = "%s-teapot_bty_3D" % frameNum
        runFrame.command = "/usr/bin/env VNP_APPLICATION_TIME=1197683283873 /usr/bin/env VNP_VCR_SESSION=3411896 /usr/bin/env PROFILE=default /shots/edu/home/perl/etc/qwrap.cuerun /shots/edu/trn_jwelborn/cue/jwelborn olrun /shots/edu/trn_jwelborn/cue/cue_archive/edu-trn_jwelborn-jwelborn_teapot_bty/v4/teapot_bty.outline %d -batch -event teapot_bty_3D" % int(frameNum)
        runFrame.user_name = "jwelborn"
        runFrame.log_dir = "/mcp" # This would be on the shottree
        runFrame.show = "edu"
        runFrame.shot = "trn_jwelborn"
        runFrame.uid = 10164
        runFrame.num_cores = 100

        rqdHost.launchFrame(runFrame)

    if args.test == 'script_frame':
        print("Launching script test frame (logs to /mcp)")
        runFrame = rqd.compiled_proto.rqd_pb2.RunFrame()
        runFrame.resource_id = "8888888877777755555"
        runFrame.job_id = "SD6F3S72DJ26236KFS"
        runFrame.job_name = "swtest-home-jwelborn_rqd_test"
        runFrame.frame_id = "FD1S3I154O646UGSNN" + str(random.randint(0, 99999))
        runFrame.frame_name = "0001-preprocess"
        # Script output is not buffered due to python -u option
        runFrame.command = "/net/people/jwelborn/test_python_u -t 5 -e 0"
        runFrame.user_name = "jwelborn"
        runFrame.log_dir = "/mcp" # This would be on the shottree
        runFrame.show = "swtest"
        runFrame.shot = "home"
        runFrame.uid = 10164
        runFrame.num_cores = 50

        rqdHost.launchFrame(runFrame)

    if args.test == 'script_frame_mac':
        print("Launching script test frame (logs to /tmp)")
        runFrame = rqd.compiled_proto.rqd_pb2.RunFrame()
        runFrame.resource_id = "2222222277777755555"
        runFrame.job_id = "SD6F3S72DJ26236KFS"
        runFrame.job_name = "swtest-home-jwelborn_rqd_test"
        runFrame.frame_id = "FD1S3I154O646UGSNN" + str(random.randint(0, 99999))
        runFrame.frame_name = "0001-preprocess"
        # Script output is not buffered due to python -u option
        runFrame.command = "/net/people/jwelborn/test_python_u_mac -t 5 -e 0"
        runFrame.user_name = "jwelborn"
        runFrame.log_dir = "/tmp" # This would be on the shottree
        runFrame.show = "swtest"
        runFrame.shot = "home"
        runFrame.uid = 10164
        runFrame.num_cores = 1

        rqdHost.launchFrame(runFrame)
     
     
         
     
if __name__ == "__main__":
     main()
