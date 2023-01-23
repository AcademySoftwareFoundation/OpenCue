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


"""
Initializes and starts RQD.

- RQD allows the cuebot to launch frames on a remote host.
- RQD monitors the resources on a machine.
- Frames can be monitored or killed.
- Status updates are sent to the cuebot every 60 seconds.
- Nimby built into RQD allows a desktop to be used as a render machine when
  not in use.
- See the rqnetwork module for a description of ICE interfaces.

Optional configuration file:
----------------------------
In /etc/opencue/rqd.conf (on Linux) or %LOCALAPPDATA%/OpenCue/rqd.conf (on Windows):
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

    consolehandler = logging.StreamHandler()
    consolehandler.setLevel(rqd.rqconstants.CONSOLE_LOG_LEVEL)
    consolehandler.setFormatter(logging.Formatter(rqd.rqconstants.LOG_FORMAT))
    logging.getLogger('').addHandler(consolehandler)

    if platform.system() in ('Linux', 'Darwin'):
        if platform.system() == 'Linux':
            syslogAddress = '/dev/log'
        else:
            syslogAddress = '/var/run/syslog'
        if os.path.exists(syslogAddress):
            logfile = logging.handlers.SysLogHandler(address=syslogAddress)
        else:
            logfile = logging.handlers.SysLogHandler()
    elif platform.system() == 'Windows':
        logfile = logging.FileHandler(os.path.expandvars('%TEMP%/openrqd.log'))
    else:
        logfile = logging.handlers.SysLogHandler()
    logfile.setLevel(rqd.rqconstants.FILE_LOG_LEVEL)
    logfile.setFormatter(logging.Formatter(rqd.rqconstants.LOG_FORMAT))
    logging.getLogger('').addHandler(logfile)
    logging.getLogger('').setLevel(logging.DEBUG)


def usage():
    """Prints command line syntax"""
    usage_msg = f"""SYNOPSIS
  {sys.argv[0]} [options]

  -d | --daemon          => Run as daemon
       --nimbyoff        => Disables nimby activation
  -c                     => Provide an alternate config file
                            On Linux: defaults to /etc/opencue/rqd.conf
                            On Windows: Defaults to %LOCALAPPDATA%/OpenCue/rqd.conf
                            Config file is optional
"""
    print(usage_msg, file=sys.stderr)


def main():
    """Entrypoint for RQD."""
    setupLogging()

    if platform.system() == 'Linux' and os.getuid() != 0 and \
       rqd.rqconstants.RQD_BECOME_JOB_USER:
        logging.critical("Please run launch as root")
        sys.exit(1)

    try:
        opts, _ = getopt.getopt(sys.argv[1:], 'hdc:', ['help', 'daemon', 'nimbyoff', 'update'])
    except getopt.GetoptError:
        usage()
        sys.exit(1)

    optNimbyOff = False
    for option, _ in opts:
        if option in ["-h", "--help"]:
            usage()
            sys.exit(0)
        if option in ["-d", "--daemon"]:
            # TODO(bcipriano) Background the process. (Issue #153)
            pass
        if option in ["--nimbyoff"]:
            optNimbyOff = True

    rqd.rqutil.permissionsLow()

    logging.warning('RQD Starting Up')

    rqCore = rqd.rqcore.RqCore(optNimbyOff)
    rqCore.start()


if __name__ == "__main__":
    main()
