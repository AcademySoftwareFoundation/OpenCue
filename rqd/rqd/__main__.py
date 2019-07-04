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

Project: RQD

Module: rqd.py

Project Description:
  - RQD allows the cuebot to launch frames on a remote host.
  - RQD monitors the resources on a machine.
  - Frames can be monitored or killed.
  - Status updates are sent to the cuebot every 60 seconds.
  - Nimby built into RQD allows a desktop to be used as a render machine when
    not in use.
  - See the rqnetwork module for a description of ICE interfaces.

SVN Path:
   - http://softboss/svn/repos/middle-tier/rqd/trunk
Requires: ./spi-slice from:
   - http://softboss/svn/repos/middle-tier/cuebot/branches/jwelborn/spi-slice
Requires: ./slice from:
   - http://softboss/svn/repos/middle-tier/cuebot/branches/jwelborn/slice

Contact: Middle-Tier

For RQD Maintainer only:
========================
  To install rqd on a machine manually:
  -------------------------------------
    - sudo mkdir /usr/local/spi/bin/rqd3
    - cd /usr/local/spi/bin/rqd3
    - sudo icepatch2client --IcePatch2.Endpoints="tcp -h genosis -p 12000" -t
    - sudo ln -s /usr/local/spi/bin/rqd3/rqd3_init.d /etc/init.d/rqd3
    - sudo /sbin/chkconfig --add rqd3

  To create the rpm: (don't do this)
  ----------------------------------
    - cd /net/yum/jwelborn/rpm-rhel40
    - mkdir -p /var/tmp/yum-rpm-build-scratch/$USER/BUILD_i386
    - nano ./SPECS/spi-rqd3.spec
    - rpmbuild -ba ./SPECS/spi-rqd3.spec

  To install on a machine with rpm:
  ---------------------------------
    - sudo rsh HOSTNAME rpm -ivh
      /net/yum/jwelborn/rpm-rhel40/RPMS/i386/spi-rqd3-0.1.0-1.i386.rpm

  To uninstall from a machine with rpm:
  -------------------------------------
    - sudo rsh HOSTNAME rpm -e spi-rqd3-0.1.0-1

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

SVN: $Id$
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function


import getopt
import logging as log
import os
import platform
import socket
import sys
from logging.handlers import SysLogHandler


def setupLogging():
    """Sets up the logging for RQD.
       Logs to /var/log/messages"""
    # TODO(bcipriano) These should be config based. (Issue #72)
    consoleFormat = '%(asctime)s %(levelname)-9s rqd3-%(module)-10s %(message)s'
    consoleLevel  = log.DEBUG
    fileFormat    = '%(asctime)s %(levelname)-9s rqd3-%(module)-10s %(message)s'
    fileLevel     = log.WARNING # Equal to or greater than the consoleLevel

    log.basicConfig(level=consoleLevel, format=consoleFormat)
    try:
        logfile = SysLogHandler(address='/dev/log')
    except socket.error:
        logfile = SysLogHandler()
    logfile.setLevel(fileLevel)
    logfile.setFormatter(log.Formatter(fileFormat))
    log.getLogger('').addHandler(logfile)

setupLogging()

from rqd.rqcore import RqCore
from rqd import rqutil
from rqd import rqconstants

def usage():
    """Prints command line syntax"""
    synopsis = ("SYNOPSIS",
                "   {} [options]\n".format(sys.argv[0]),
                "  -d | --daemon          => Run as daemon",
                "       --nimbyoff        => Disables nimby activation",
                "  -c                     => Provide an alternate config file",
                "                            Defaults to /etc/rqd3/rqd3.conf",
                "                            Config file is optional\n")
    sys.stderr.write("\n".join(synopsis))

def main():
    if platform.system() == 'Linux' and os.getuid() != 0:
        log.critical("Please run launch as root")
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

    rqutil.permissionsLow()

    log.warning('RQD Starting Up')

    if rqconstants.FACILITY in ('abq'):
        os.environ['TZ'] = 'PST8PDT'

    rqd = RqCore(optNimbyOff)
    rqd.start()


if __name__ == "__main__":
  main()

