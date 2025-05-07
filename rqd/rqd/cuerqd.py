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


"""Displays information from or sends a command to an RQD host."""


from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import argparse
from builtins import str
from builtins import object
import logging as log
import os
import random

import grpc

import rqd.compiled_proto.rqd_pb2
import rqd.compiled_proto.rqd_pb2_grpc
import rqd.rqconstants


class RqdHost(object):
    """An RQD host.

    This class supplies a wrapper for querying or sending commands to an RQD host."""

    def __init__(self, rqdHost, rqdPort=rqd.rqconstants.RQD_GRPC_PORT):
        self.rqdHost = rqdHost
        self.rqdPort = rqdPort

        channel = grpc.insecure_channel('%s:%s' % (self.rqdHost, self.rqdPort))
        self.stub = rqd.compiled_proto.rqd_pb2_grpc.RqdInterfaceStub(channel)
        self.frameStub = rqd.compiled_proto.rqd_pb2_grpc.RunningFrameStub(channel)

    def status(self):
        """Fetches and returns the host status report."""
        return self.stub.ReportStatus(rqd.compiled_proto.rqd_pb2.RqdStaticReportStatusRequest())

    def getRunningFrame(self, frameId):
        """Returns the host's currently running frame."""
        return self.stub.GetRunFrame(
            rqd.compiled_proto.rqd_pb2.RqdStaticGetRunFrameRequest(frame_id=frameId))

    def nimbyOff(self):
        """Disables Nimby on the host."""
        log.info(self.rqdHost, "Turning off Nimby")
        log.info("rqd nimbyoff by %s", os.environ.get("USER"))
        self.stub.NimbyOff(rqd.compiled_proto.rqd_pb2.RqdStaticNimbyOffRequest())

    def nimbyOn(self):
        """Enables Nimby on the host."""
        log.info(self.rqdHost, "Turning on Nimby")
        log.info("rqd nimbyon by %s", os.environ.get("USER"))
        self.stub.NimbyOn(rqd.compiled_proto.rqd_pb2.RqdStaticNimbyOnRequest())

    def lockAll(self):
        """Locks all of the host's cores."""
        print(self.rqdHost, "Locking all cores")
        self.stub.LockAll(rqd.compiled_proto.rqd_pb2.RqdStaticLockAllRequest())

    def unlockAll(self):
        """Unlocks all of the host's cores."""
        print(self.rqdHost, "Unlocking all cores")
        self.stub.UnlockAll(rqd.compiled_proto.rqd_pb2.RqdStaticUnlockAllRequest())

    def lock(self, cores):
        """Locks the given number of cores."""
        cores = int(cores)
        print(self.rqdHost, "Locking %d cores" % cores)
        self.stub.Lock(rqd.compiled_proto.rqd_pb2.RqdStaticLockRequest(cores=cores))

    def unlock(self, cores):
        """Unlocks the given number of cores."""
        cores = int(cores)
        print(self.rqdHost, "Unlocking %d cores" % cores)
        self.stub.Unlock(rqd.compiled_proto.rqd_pb2.RqdStaticUnlockRequest(cores=cores))

    def shutdownRqdIdle(self):
        """Shuts down the host when idle."""
        print(self.rqdHost, "Sending shutdownRqdIdle command")
        self.stub.ShutdownRqdIdle(rqd.compiled_proto.rqd_pb2.RqdStaticShutdownIdleRequest())

    def shutdownRqdNow(self):
        """Shuts down the host now."""
        print(self.rqdHost, "Sending shutdownRqdNow command")
        try:
            self.stub.ShutdownRqdNow(rqd.compiled_proto.rqd_pb2.RqdStaticShutdownNowRequest())
        # pylint: disable=broad-except
        except Exception:
            # Shutting down the service from inside means this request will receive
            # a connection error response
            pass

    def restartRqdIdle(self):
        """Restarts RQD on the host when idle."""
        print(self.rqdHost, "Sending restartRqdIdle command")
        self.stub.RestartRqdIdle(rqd.compiled_proto.rqd_pb2.RqdStaticRestartIdleRequest())

    def rebootIdle(self):
        """Reboots the host when idle."""
        print(self.rqdHost, "Sending rebootIdle command")
        self.stub.RebootIdle(rqd.compiled_proto.rqd_pb2.RqdStaticRebootIdleRequest())

    def rebootNow(self):
        """Reboots the host now."""
        print(self.rqdHost, "Sending rebootNow command")
        self.stub.RebootNow(rqd.compiled_proto.rqd_pb2.RqdStaticRebootNowRequest())

    def launchFrame(self, frame):
        """Launches a frame on the host."""
        self.stub.LaunchFrame(
            rqd.compiled_proto.rqd_pb2.RqdStaticLaunchFrameRequest(run_frame=frame))

    def killFrame(self, frameId, message):
        """Kills a frame on the host."""
        runFrame = self.getRunningFrame(frameId)
        self.frameStub.Kill(run_frame=runFrame, message=message)


def main():
    """Entrypoint for the commandline interface."""

    parser = argparse.ArgumentParser()

    parser.add_argument(
        'host', nargs='?', default='localhost', help='RQD hostname (defaults to localhost)')
    parser.add_argument(
        '-s', action='store_true', help='Print RQD status')
    parser.add_argument(
        '-v', action='store_true', help='Print RQD version')
    parser.add_argument(
        '--lp', metavar='coreID', nargs='+', help='Lock the specified cores')
    parser.add_argument(
        '--ulp', metavar='coreID', nargs='+', help='Unlock the specified cores')
    parser.add_argument(
        '--lh', action='store_true', help='Lock all cores for the specified host')
    parser.add_argument(
        '--ulh', action='store_true', help='Unlock all cores for the specified host')
    parser.add_argument(
        '--nimbyon', action='store_true',
        help="Turn on 'Not in my back yard' (NIMBY) to stop processing on the specified host")
    parser.add_argument(
        '--nimbyoff', action='store_true',
        help="Turn off 'Not in my back yard' (NIMBY) to start processing on the specified host")
    parser.add_argument(
        '--exit', action='store_true',
        help='Lock host, wait until machine is idle, and then shutdown RQD. Any unlock '
             'command cancels this request.')
    parser.add_argument(
        '--exit_now', action='store_true', help='KILL ALL running frames and shutdown RQD')
    parser.add_argument(
        '--restart', action='store_true',
        help='Lock host, wait until machine is idle, and then restart RQD. Any unlock '
             'command cancels this request')
    parser.add_argument(
        '--reboot', action='store_true',
        help='Lock host, wait until machine is idle, and then REBOOT machine. Any unlock '
             'command cancels this request.')
    parser.add_argument(
        '--reboot_now', action='store_true', help='KILL ALL running frames and REBOOT machine')
    parser.add_argument(
        '--kill', metavar='frameID', nargs='+',
        help='Attempts to kill the given frame via its ICE proxy')
    parser.add_argument(
        '--getproxy', metavar='frameID', nargs='+', help='Returns the proxy for the given frameid')
    parser.add_argument(
        '--test_edu_frame', action='store_true',
        help='Launch an edu frame test on an idle core (or first core if none are available)')
    parser.add_argument(
        '--test_script_frame', action='store_true',
        help='Launch a script frame test on an idle core (or first core if none are available)')
    parser.add_argument(
        '--test_script_frame_mac', action='store_true',
        help='Launch a script frame test for macOS on an idle core (or first core if '
             'none are available)')

    args = parser.parse_args()

    rqdHost = RqdHost(args.host)

    if args.s:
        print(rqdHost.status())

    if args.v:
        tagPrefix = 'rqdv-'
        for tag in rqdHost.status().host.tags:
            if tag.startswith(tagPrefix):
                print("version =", tag[len(tagPrefix):])

    if args.nimbyoff:
        rqdHost.nimbyOff()

    if args.nimbyon:
        rqdHost.nimbyOn()

    if args.lp is not None:
        for arg in args.lp:
            rqdHost.lock(arg)

    if args.ulp is not None:
        for arg in args.ulp:
            rqdHost.unlock(arg)

    if args.lh is not None:
        rqdHost.lockAll()

    if args.ulh is not None:
        rqdHost.unlockAll()

    if args.exit_now:
        rqdHost.shutdownRqdNow()

    elif args.exit:
        rqdHost.shutdownRqdIdle()

    elif args.restart:
        rqdHost.restartRqdIdle()

    elif args.reboot_now:
        rqdHost.rebootNow()

    elif args.reboot:
        rqdHost.rebootIdle()

    if args.kill is not None:
        for arg in args.kill:
            rqdHost.killFrame(arg, "Killed by %s using cuerqd.py" % os.environ.get("USER"))

    if args.getproxy is not None:
        for arg in args.getproxy:
            frameProxy = rqdHost.getRunningFrame(arg)
            print(frameProxy)

    if args.test_edu_frame:
        print("Launching edu test frame (logs to /mcp)")
        frameNum = "0001"
        runFrame = rqd.compiled_proto.rqd_pb2.RunFrame()
        runFrame.job_id = "SD6F3S72DJ26236KFS"
        runFrame.job_name = "edu-trn_jwelborn-jwelborn_teapot_bty"
        runFrame.frame_id = "FD1S3I154O646UGSNN%s" % frameNum
        runFrame.frame_name = "%s-teapot_bty_3D" % frameNum
        runFrame.command = (
                "/usr/bin/env VNP_APPLICATION_TIME=1197683283873 /usr/bin/env VNP_VCR_"
                "SESSION=3411896 /usr/bin/env PROFILE=default "
                "/shots/edu/home/perl/etc/qwrap.cuerun /shots/edu/trn_jwelborn/cue/jwelborn "
                "olrun /shots/edu/trn_jwelborn/cue/cue_archive/edu-trn_jwelborn-jwelborn_teapot_bty"
                "/v4/teapot_bty.outline %d -batch -event teapot_bty_3D" % int(frameNum))
        runFrame.user_name = "jwelborn"
        runFrame.log_dir = "/mcp" # This would be on the shottree
        runFrame.show = "edu"
        runFrame.shot = "trn_jwelborn"
        runFrame.uid = 10164
        runFrame.num_cores = 100
        rqdHost.launchFrame(runFrame)

    if args.test_script_frame:
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

    if args.test_script_frame_mac:
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
