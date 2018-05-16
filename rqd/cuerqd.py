#!/usr/bin/python


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




# Note: Python on mac = /opt/local/bin/python2.4
"""SYNOPSIS
     cuerqd [hostname] [OPTIONS]
      [hostname]            => RQD hostname (defaults to localhost)
      -s                    => Print rqd status
      -v                    => Print rqd version
      --lp <cores>          => Lock Cores
      --ulp <cores>         => Unlock Cores
      --lh                  => Lock Host (All Cores)
      --ulh                 => Unlock Host (All Cores)
      --nimbyoff            => Turn on Nimby
      --nimbyon             => Turn off Nimby
      --exit                => Lock host, wait until machine is idle and then Shutdown RQD *
      --exit_now            => KILL ALL running frames and Shutdown RQD
      --restart             => Lock host, wait until machine is idle and then Restart RQD *
      --restart_now         => KILL ALL running frames and Restart RQD
      --reboot              => Lock host, wait until machine is idle and then REBOOT machine *
      --reboot_now          => KILL ALL running frames and REBOOT machine
    print
      --kill <frameid>      => Attempts to kill the given frame via its ICE proxy
      --getproxy <frameid>  => Returns the proxy for the given frameid (debug)
    print
     * Any unlock command will cancel this request
\n FOR TESTING:
      --test_edu_frame        => Launch a test edu frame on an idle core
                                Use first core if none are available
      --test_script_frame     => Same as above but launches a 5 second python script
      --test_script_frame_mac => Same as above but for mac host
\nDESCRIPTION
      Displays information from or sends a command to an RQD host
\nCONTACT
     Middle-Tier Group (middle-tier@imageworks.com)"""

import os
import sys
import getopt
import re
import random

lib_path = os.path.abspath(os.path.dirname(__file__))

# Needed due to segfault from loadSlice when in a protected directory
os.chdir("/tmp")

import python_ice_server.loader
python_ice_server.loader.setup_python_for_ice_3_3()

import rqconstants
import rqutil
import logging as log

import Ice
Ice.loadSlice("--all -I{PATH}/slice/spi -I{PATH}/slice/cue {PATH}/slice/cue/" \
              "rqd_ice.ice".replace("{PATH}", lib_path))
import cue.RqdIce as RqdIce

class RqdHost:
    def __init__(self, rqd_host,
                 string_from_cuebot = rqconstants.STRING_FROM_CUEBOT,
                 rqd_port = rqconstants.RQD_PORT):
        self.rqd_host = rqd_host
        self.rqd_port = rqd_port

        init_data = Ice.InitializationData()
        props = init_data.properties = Ice.createProperties()

        if Ice.intVersion() >= 30600:
            props.setProperty('Ice.ACM.Client.Timeout', '60',)
            # Don't close connection when waiting for a response
            # from a server running Ice < 3.6.
            # Can remove when server is Ice >= 3.6.
            props.setProperty('Ice.ACM.Client.Close', '1',)
        else:
            props.setProperty('Ice.ACM.Client', '2',)

        # Allow Ice 3.5 clients, remove when server is also Ice 3.5
        if Ice.intVersion() >= 30500:
            props.setProperty('Ice.Default.EncodingVersion', '1.0')

        self.communicator = Ice.initialize(init_data)

        try:
            self.DataToRQD = RqdIce.RqdStaticPrx.checkedCast(self.communicator.stringToProxy(string_from_cuebot + ':tcp -h ' + rqd_host + ' -p ' + rqd_port))
        except Exception, e:
            print "Unable to connect to rqd on host=", rqd_host, "with port=", rqd_port
            print Exception
            print e
            sys.exit()
        print "Connection to RQD", rqd_host, "on port", rqd_port, "established"

    def __del__(self):
        self.communicator.destroy()

    def status(self):
        return self.DataToRQD.reportStatus()

    def getRunningFrame(self, frameId):
        return self.DataToRQD.getRunningFrame(frameId)

    def nimbyOff(self):
        print self.rqd_host,"Turning off Nimby"
        log.info("rqd nimbyoff by {0}".format(os.environ.get("USER")))
        self.DataToRQD.nimbyOff()

    def nimbyOn(self):
        print self.rqd_host,"Turning on Nimby"
        log.info("rqd nimbyon by {0}".format(os.environ.get("USER")))
        self.DataToRQD.nimbyOn()

    def lockAll(self):
        print self.rqd_host,"Locking all cores"
        self.DataToRQD.lockAll()

    def unlockAll(self):
        print self.rqd_host,"Unlocking all cores"
        self.DataToRQD.unlockAll()

    def lock(self, cores):
        cores = int(cores)
        print self.rqd_host,"Locking %d cores" % cores
        self.DataToRQD.lock(cores)

    def unlock(self, cores):
        cores = int(cores)
        print self.rqd_host,"Unlocking %d cores" % cores
        self.DataToRQD.unlock(cores)

    def shutdownRqdIdle(self):
        print self.rqd_host,"Sending shutdownRqdIdle command"
        self.DataToRQD.shutdownRqdIdle()

    def shutdownRqdNow(self):
        print self.rqd_host,"Sending shutdownRqdNow command"
        self.DataToRQD.shutdownRqdNow()

    def restartRqdIdle(self):
        print self.rqd_host,"Sending restartRqdIdle command"
        self.DataToRQD.restartRqdIdle()

    def restartRqdNow(self):
        print self.rqd_host,"Sending restartRqdNow command"
        self.DataToRQD.restartRqdNow()

    def rebootIdle(self):
        print self.rqd_host,"Sending rebootIdle command"
        self.DataToRQD.rebootIdle()

    def rebootNow(self):
        print self.rqd_host,"Sending rebootNow command"
        self.DataToRQD.rebootNow()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print __doc__
        sys.exit()
    elif sys.argv[1].startswith("-"):
        hostname = "localhost"
        start_argv = sys.argv[1:]
    else:
        hostname = sys.argv[1]
        start_argv = sys.argv[2:]

    try:
        SHORT_ARGS = 'hsv'
        LONG_ARGS = ['help', 'lh', 'ulh', 'ulp=', 'lp=', 'nimbyoff', 'nimbyon',
                     'exit', 'exit_now', 'test_edu_frame', 'test_script_frame',
                     'test_script_frame_mac', "kill=","restart", "restart_now",
                     "reboot", "reboot_now", "getproxy=", "s"]
        newargs = [re.sub(r"^(-\w{2,})$", r"-\1", arg) for arg in start_argv]
        opts, argv = getopt.getopt(newargs, SHORT_ARGS, LONG_ARGS)
    except getopt.GetoptError:
        print __doc__
        sys.exit(1)

    rqdHost = RqdHost(hostname)

    for o, a in opts:
        if o in ("-h","--help"):
            print __doc__
            sys.exit(0)
        if o in ("-s", "--s"):
            print rqdHost.status()
        if o in ("-v",):
            tag_prefix = 'rqdv-'
            for tag in rqdHost.status().host.tags:
                if tag.startswith(tag_prefix):
                    print "version =", tag[len(tag_prefix):]
        if o == "--nimbyoff":
            rqdHost.nimbyOff()
        if o == "--nimbyon":
            rqdHost.nimbyOn()
        if o == "--lh":
            rqdHost.lockAll()
        if o == "--ulh":
            rqdHost.unlockAll()
        if o == "--lp":
            rqdHost.lock(a)
        if o == "--ulp":
            rqdHost.unlock(a)
        if o == "--exit":
            rqdHost.shutdownRqdIdle()
        if o == "--exit_now":
            rqdHost.shutdownRqdNow()
        if o == "--restart":
            rqdHost.restartRqdIdle()
        if o == "--restart_now":
            rqdHost.restartRqdNow()
        if o == "--reboot":
            rqdHost.rebootIdle()
        if o == "--reboot_now":
            rqdHost.rebootNow()
        if o == "--getproxy":
            frameProxy = rqdHost.getRunningFrame(a)
            print frameProxy
        if o == "--kill":
            frameProxyStr = "RunningFrame/%s -t:tcp -h %s -p %s" % \
                            (a, hostname, rqdHost.rqd_port)
            try:
                frameProxy = RqdIce.RunningFramePrx.checkedCast(rqdHost.communicator.stringToProxy(frameProxyStr))
                frameProxy.kill("Killed by %s using cuerqd.py" % os.environ.get("USER"))
                print "Sent kill to frame: %s" % frameProxyStr
            except Exception, e:
                print "Unable to connect with proxy: %s" % frameProxyStr
                print e

        if o == "--test_edu_frame":
            print "Launching edu test frame (logs to /mcp)"
            frameNum = "0001"
            runFrame = RqdIce.RunFrame()
            runFrame.jobId = "SD6F3S72DJ26236KFS"
            runFrame.jobName = "edu-trn_jwelborn-jwelborn_teapot_bty"
            runFrame.frameId = "FD1S3I154O646UGSNN%s" % frameNum
            runFrame.frameName = "%s-teapot_bty_3D" % frameNum
            runFrame.command = "/usr/bin/env VNP_APPLICATION_TIME=1197683283873 /usr/bin/env VNP_VCR_SESSION=3411896 /usr/bin/env PROFILE=default /shots/edu/home/perl/etc/qwrap.cuerun /shots/edu/trn_jwelborn/cue/jwelborn olrun /shots/edu/trn_jwelborn/cue/cue_archive/edu-trn_jwelborn-jwelborn_teapot_bty/v4/teapot_bty.outline %d -batch -event teapot_bty_3D" % int(frameNum)
            runFrame.userName = "jwelborn"
            runFrame.logDir = "/mcp" # This would be on the shottree
            runFrame.show = "edu"
            runFrame.shot = "trn_jwelborn"
            runFrame.uid = 10164

            #report = rqdHost.status()
            #if report.coreInfo.idleCores >= 100

            runFrame.numCores = 100

            frameProxy = rqdHost.DataToRQD.launchFrame(runFrame)
        if o == "--test_script_frame":
            print "Launching script test frame (logs to /mcp)"
            runFrame = RqdIce.RunFrame()
            runFrame.resourceId = "8888888877777755555"
            runFrame.jobId = "SD6F3S72DJ26236KFS"
            runFrame.jobName = "swtest-home-jwelborn_rqd_test"
            runFrame.frameId = "FD1S3I154O646UGSNN" + str(random.randint(0, 99999))
            runFrame.frameName = "0001-preprocess"
            # Script output is not buffered due to python -u option
            runFrame.command = "/net/people/jwelborn/test_python_u -t 5 -e 0"
            runFrame.userName = "jwelborn"
            runFrame.logDir = "/mcp" # This would be on the shottree
            runFrame.show = "swtest"
            runFrame.shot = "home"
            runFrame.uid = 10164
            #runFrame.type = CueIce.LayerType.Render
            #report = rqdHost.status()
            #if report.coreInfo.idleCores >= 100
            runFrame.numCores = 50

            frameProxy = rqdHost.DataToRQD.launchFrame(runFrame)
        if o == "--test_script_frame_mac":
            print "Launching script test frame (logs to /tmp)"
            runFrame = RqdIce.RunFrame()
            runFrame.resourceId = "2222222277777755555"
            runFrame.jobId = "SD6F3S72DJ26236KFS"
            runFrame.jobName = "swtest-home-jwelborn_rqd_test"
            runFrame.frameId = "FD1S3I154O646UGSNN" + str(random.randint(0, 99999))
            runFrame.frameName = "0001-preprocess"
            # Script output is not buffered due to python -u option
            runFrame.command = "/net/people/jwelborn/test_python_u_mac -t 5 -e 0"
            runFrame.userName = "jwelborn"
            runFrame.logDir = "/tmp" # This would be on the shottree
            runFrame.show = "swtest"
            runFrame.shot = "home"
            runFrame.uid = 10164
            #report = rqdHost.status()
            #if report.coreInfo.idleCores >= 100
            runFrame.numCores = 1.0

            frameProxy = rqdHost.DataToRQD.launchFrame(runFrame)

