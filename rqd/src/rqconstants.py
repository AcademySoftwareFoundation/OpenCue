
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
Constants.

Project: RQD

Module: rqcore.py

Contact: Middle-Tier

SVN: $Id$
"""
import os
import sys
import platform
import logging
import traceback
import commands
import platform
import re

if platform.system() == 'Linux':
    import pwd

import Ice

Ice.loadSlice("--all -I{PATH}/slice/spi -I{PATH}/slice/cue {PATH}/slice/cue/" \
              "rqd_ice.ice".replace("{PATH}", os.path.dirname(__file__)))
import cue.CueIce

import rqutil

# This value is replaced during rpm build to look like:
# VERSION = '20171128-bc7c070a'
VERSION = 'dev'

RQD_LOCAL_PATH = "/usr/local/spi/rqd3"

# ICE connection information:
STRING_FROM_CUEBOT = "RqdStatic"
STRING_TO_CUEBOT = "RqdReportStatic"
CUEBOT_PORT = "9018"

# If the hostname is blank then the facility ice server will be queried
# Multiple hosts can be listed as space delimited
# TODO: Make driven by a config file b/110168575
# CUEBOT_HOSTNAME = "cue3bot1 cue3bot2 cue3bot3"
if 'CUEBOT_HOSTNAME' in os.environ:
  CUEBOT_HOSTNAME = os.environ['CUEBOT_HOSTNAME']
else:
  CUEBOT_HOSTNAME = "localhost"

RQD_PORT = "10021"
RQD_HOST = "localhost"
RQD_TIMEOUT = "10000"

FACILITY_ICE_NAMESERVER = "FacilityStatic" \
                          ":tcp -h ice-ns1 -p 30000 -t 2000" \
                          ":tcp -h ice-ns2 -p 30000 -t 2000"


# GRPC VALUES
RQD_GRPC_MAX_WORKERS = 10
RQD_GRPC_PORT = 50051
RQD_GRPC_SLEEP = 60 * 60 *24


# RQD behavior:
RSS_UPDATE_INTERVAL = 10
RQD_PING_INTERVAL = 60
MAX_LOG_FILES = 15
CORE_VALUE = 100
LAUNCH_FRAME_USER_GID = 20
RQD_RETRY_STARTUP_CONNECT_DELAY = 30
RQD_RETRY_CRITICAL_REPORT_DELAY = 30

KILL_SIGNAL = 9
if platform.system() == 'Linux':
    RQD_UID = pwd.getpwnam("daemon")[2]
    RQD_GID = pwd.getpwnam("daemon")[3]
else:
    RQD_UID = 0
    RQD_GID = 0

# ptree reporting is not actually used, and could be slow
ENABLE_PTREE = False

# Nimby behavior:
CHECK_INTERVAL_LOCKED = 60  # = seconds to wait before checking if the user has become idle
MINIMUM_IDLE = 900          # seconds of idle time required before nimby unlocks
MINIMUM_MEM = 524288        # If available memory drops below this amount, lock nimby (need to take into account cache)
MINIMUM_SWAP = 1048576
MAXIMUM_LOAD = 75           # If (machine load * 100 / cores) goes over this amount, don't unlock nimby
                            # 1.5 would mean a max load of 1.5 per core

EXITSTATUS_FOR_FAILED_LAUNCH = cue.CueIce.FrameExitStatusNoRetry
EXITSTATUS_FOR_NIMBY_KILL = cue.CueIce.FrameExitStatusSkipRetry

PATH_CPUINFO = "/proc/cpuinfo"
PATH_INITTAB = "/etc/inittab" # spinux1
PATH_INIT_TARGET = '/lib/systemd/system/default.target' # rhel7
PATH_LOADAVG = "/proc/loadavg"
PATH_STAT = "/proc/stat"
PATH_MEMINFO = "/proc/meminfo"

if platform.system() == 'Linux':
    SYS_HERTZ = os.sysconf('SC_CLK_TCK')

CONFIG_FILE = "/etc/rqd3/rqd3.conf"
if "-c" in sys.argv:
    CONFIG_FILE = sys.argv[sys.argv.index("-c") + 1]

OVERRIDE_CORES = None # number of cores. ex: None or 8
OVERRIDE_IS_DESKTOP = None # Force rqd to run in 'desktop' mode
OVERRIDE_PROCS = None # number of physical cpus. ex: None or 2
OVERRIDE_MEMORY = None # in Kb
OVERRIDE_NIMBY = None # True to turn on, False to turn off
ALLOW_GPU = False
ALLOW_PLAYBLAST = False
LOAD_MODIFIER = 0 # amount to add/subtract from load

if commands.getoutput('/bin/su --help').find('session-command') != -1:
    SU_ARGUEMENT = '--session-command'
else:
    SU_ARGUEMENT = '-c'

SP_OS = FACILITY = ''
if os.path.isfile('/usr/local/stdenv/.cshrc'):
    SP_OS, FACILITY = commands.getoutput("csh -c 'unsetenv SP_PATH ; setenv CONSOLE 1 ; setenv HOME / ; source /usr/local/stdenv/.cshrc ; echo $SP_OS $FACILITY'").split()[-2:]
elif os.path.isfile('/etc/csh.cshrc'):
    # For maa on centos
    SP_OS, FACILITY = commands.getoutput("csh -c 'source /etc/csh.cshrc ; echo $SP_OS $FACILITY'").split()[-2:]
if not 3 <= len(SP_OS) <= 10 or not re.match('^[A-Za-z0-9]*$', SP_OS):
    if SP_OS:
        logging.warning('SP_OS value of %s is out of allowed range' % SP_OS)
    SP_OS = platform.system()
if len(FACILITY) != 3 or not re.match('^[A-Za-z0-9]*$', FACILITY):
    if FACILITY:
        logging.warning('FACILITY value of %s is out of allowed range' % FACILITY)
    FACILITY = 'lax'

# maa is small so decrease the ping in interval
if FACILITY == 'maa':
    RQD_PING_INTERVAL = 30

try:
    if os.path.isfile(CONFIG_FILE):
        # Hostname can come from here: rqutil.getHostname()
        __section = "Override"
        import ConfigParser
        config = ConfigParser.RawConfigParser()
        config.read(CONFIG_FILE)
        if config.has_option(__section, "OVERRIDE_CORES"):
            OVERRIDE_CORES = config.getint(__section, "OVERRIDE_CORES")
        if config.has_option(__section, "OVERRIDE_PROCS"):
            OVERRIDE_PROCS = config.getint(__section, "OVERRIDE_PROCS")
        if config.has_option(__section, "OVERRIDE_MEMORY"):
            OVERRIDE_MEMORY = config.getint(__section, "OVERRIDE_MEMORY")
        if config.has_option(__section, "OVERRIDE_CUEBOT"):
            CUEBOT_HOSTNAME = config.get(__section, "OVERRIDE_CUEBOT")
        if config.has_option(__section, "OVERRIDE_NIMBY"):
            OVERRIDE_NIMBY = config.getboolean(__section, "OVERRIDE_NIMBY")
        if config.has_option(__section, "GPU"):
            ALLOW_GPU = config.getboolean(__section, "GPU")
        if config.has_option(__section, "PLAYBLAST"):
            ALLOW_PLAYBLAST = config.getboolean(__section, "PLAYBLAST")
        if config.has_option(__section, "LOAD_MODIFIER"):
            LOAD_MODIFIER = config.getint(__section, "LOAD_MODIFIER")
except Exception, e:
    logging.warning("Failed to read values from config file %s due to %s at %s" % (CONFIG_FILE, e, traceback.extract_tb(sys.exc_info()[2])))

