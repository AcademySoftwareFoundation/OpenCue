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


"""
Initializes and starts rqd.

- RQD allows the cuebot to launch frames on a remote host.
- RQD monitors the resources on a machine.
- Frames can be monitored or killed.
- Status updates are sent to the cuebot every 60 seconds.
- Nimby built into RQD allows a desktop to be used as a render machine when
  not in use.
- See the rqnetwork module for a description of ICE interfaces.

Optional configuration file:
----------------------------
in /etc/rqd3/rqd3.conf:
[Override]
OVERRIDE_CORES = 2
OVERRIDE_PROCS = 3
OVERRIDE_MEMORY = 1000000
OVERRIDE_CUEBOT = cuebot1 cuebot2 cuebot3
# True will start nimby, False will keep nimby from starting
OVERRIDE_NIMBY = False
# True will check and report gpu memory if cuda capable
GPU = True
# True will force 256mb gpu memory
PLAYBLAST = True
"""


from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import getopt
import logging
import logging.handlers
import os
import platform
import sys

import rqd.rqconstants
import rqd.rqcore
import rqd.rqutil


def setupLogging():
    """Sets up the logging for RQD.
       Logs to /var/log/messages"""
    # TODO(bcipriano) These should be config based. (Issue #72)
    consoleFormat = '%(asctime)s %(levelname)-9s rqd3-%(module)-10s %(message)s'
    consoleLevel  = logging.DEBUG
    fileFormat    = '%(asctime)s %(levelname)-9s rqd3-%(module)-10s %(message)s'
    fileLevel     = logging.WARNING # Equal to or greater than the consoleLevel

    logging.basicConfig(level=consoleLevel, format=consoleFormat)
    if platform.system() in ('Linux', 'Darwin'):
        if platform.system() == 'Linux':
            syslogAddress = '/dev/log'
        else:
            syslogAddress = '/var/run/syslog'
        if os.path.exists(syslogAddress):
            logfile = logging.handlers.SysLogHandler(address=syslogAddress)
        else:
            logfile = logging.handlers.SysLogHandler()
    else:
        logfile = logging.handlers.SysLogHandler()
    logfile.setLevel(fileLevel)
    logfile.setFormatter(logging.Formatter(fileFormat))
    logging.getLogger('').addHandler(logfile)


def usage():
    """Prints command line syntax"""
    s = sys.stderr
    print("SYNOPSIS", file=s)
    print("  ", sys.argv[0], "[options]\n", file=s)
    print("  -d | --daemon          => Run as daemon", file=s)
    print("       --nimbyoff        => Disables nimby activation", file=s)
    print("  -c                     => Provide an alternate config file", file=s)
    print("                            Defaults to /etc/rqd3/rqd3.conf", file=s)
    print("                            Config file is optional", file=s)

def main():
    setupLogging()

    if platform.system() == 'Linux' and os.getuid() != 0:
        logging.critical("Please run launch as root")
        sys.exit(1)

    try:
        opts, argv = getopt.getopt(sys.argv[1:], 'hdc:', ['help',
                                                          'daemon',
                                                          'nimbyoff',
                                                          'update'])
    except getopt.GetoptError:
        usage()
        sys.exit(1)

    optNimbyOff = False
    for o, a in opts:
        if o in ["-h", "--help"]:
            usage()
            sys.exit(0)
        if o in ["-d", "--daemon"]:
            # TODO(bcipriano) Background the process. (Issue #153)
            pass
        if o in ["--nimbyoff"]:
            optNimbyOff = True

    rqd.rqutil.permissionsLow()

    logging.warning('RQD Starting Up')

    if rqd.rqconstants.FACILITY == 'abq':
        os.environ['TZ'] = 'PST8PDT'

    rqCore = rqd.rqcore.RqCore(optNimbyOff)
    rqCore.start()


if __name__ == "__main__":
  main()

