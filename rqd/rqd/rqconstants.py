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


"""Constants used throughout RQD."""


from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import logging
import os
import platform
import subprocess
import sys
import traceback
import configparser

if platform.system() == 'Linux':
    import pwd

# NOTE: Some of these values can be overridden by CONFIG_FILE; see below.

VERSION = 'dev'

if 'CUEBOT_HOSTNAME' in os.environ:
    CUEBOT_HOSTNAME = os.environ['CUEBOT_HOSTNAME']
else:
    CUEBOT_HOSTNAME = 'localhost'

RQD_TIMEOUT = 10000
DEFAULT_FACILITY = 'cloud'

# GRPC VALUES
RQD_GRPC_MAX_WORKERS = 10
RQD_GRPC_PORT = 8444
RQD_GRPC_SLEEP_SEC = 60 * 60 * 24
RQD_GRPC_CONNECTION_ATTEMPT_SLEEP_SEC = 15
RQD_GRPC_RETRY_CONNECTION = True
CUEBOT_GRPC_PORT = 8443

# RQD behavior:
RSS_UPDATE_INTERVAL = 10
RQD_MIN_PING_INTERVAL_SEC = 5
RQD_MAX_PING_INTERVAL_SEC = 30
MAX_LOG_FILES = 15
CORE_VALUE = 100
LAUNCH_FRAME_USER_GID = 20
RQD_RETRY_STARTUP_CONNECT_DELAY = 30
RQD_RETRY_CRITICAL_REPORT_DELAY = 30
RQD_USE_IP_AS_HOSTNAME = True
RQD_USE_IPV6_AS_HOSTNAME = False

# Use the PATH environment variable from the RQD host.
RQD_USE_PATH_ENV_VAR = False
# Copy specific environment variable from the RQD host to the frame env.
RQD_HOST_ENV_VARS = []

# Use the environment variables from the RQD host. For variables that exist
# In cases where a variable exists on both the host and the frame object (which are
# copied during initialization), the value from the host will take precedence.
# However, the handling of the PATH variable is unique: its value from the frame
# is merged with the host's value, with the frame's value taking precedence in the
# final result. If any var is defined at RQD_HOST_ENV_VARS, this attribute is considered False.
RQD_USE_ALL_HOST_ENV_VARS = False

RQD_CUSTOM_HOME_PREFIX = None
RQD_CUSTOM_MAIL_PREFIX = None

RQD_BECOME_JOB_USER = False
RQD_CREATE_USER_IF_NOT_EXISTS = True
SENTRY_DSN_PATH = None
RQD_TAGS = ''
RQD_PREPEND_TIMESTAMP = False

KILL_SIGNAL = 9
if platform.system() == 'Linux':
    RQD_UID = pwd.getpwnam("daemon")[2]
    RQD_GID = pwd.getpwnam("daemon")[3]
    # Linux's default uid limits are documented at
    #  https://www.man7.org/linux/man-pages/man5/login.defs.5.html
    RQD_MIN_UID = 1000
    RQD_MAX_UID = 60000
else:
    RQD_UID = 0
    RQD_GID = 0
RQD_DAEMON_UID = RQD_UID

# Nimby behavior:
# Number of seconds to wait before checking if the user has become idle.
CHECK_INTERVAL_LOCKED = 60
# Seconds of idle time required before nimby unlocks.
MINIMUM_IDLE = 900
# Default display configuration in case the environment variable DISPLAY is not set
DEFAULT_DISPLAY = ":0"
RQD_DISPLAY_PATH = None
# If available memory drops below this amount, lock nimby (need to take into account cache).
MINIMUM_MEM = 524288
MINIMUM_SWAP = 1048576
# If (machine load * 100 / cores) goes over this amount, don't unlock nimby.
# 1.5 would mean a max load of 1.5 per core
MAXIMUM_LOAD = 75

EXITSTATUS_FOR_FAILED_LAUNCH = 256
EXITSTATUS_FOR_NIMBY_KILL = 286

PATH_CPUINFO = "/proc/cpuinfo"
PATH_INITTAB = "/etc/inittab" # spinux1
PATH_INIT_TARGET = '/lib/systemd/system/default.target' # rhel7
PATH_LOADAVG = "/proc/loadavg"
PATH_STAT = "/proc/stat"
PATH_MEMINFO = "/proc/meminfo"
# stat and statm are inaccurate because of kernel internal scability optimation
# stat/statm/status are inaccurate values, true values are in smaps
# but RQD user can't read smaps get:
# [Errno 13] Permission denied: '/proc/166289/smaps'
PATH_PROC_PID_STAT = "/proc/{0}/stat"
PATH_PROC_PID_STATM = "/proc/{0}/statm"
PATH_PROC_PID_CMDLINE = "/proc/{0}/cmdline"

if platform.system() == 'Linux':
    SYS_HERTZ = os.sysconf('SC_CLK_TCK')

# First retrieve local configuration file
if platform.system() == 'Windows':
    CONFIG_FILE = os.path.expandvars('%LOCALAPPDATA%/OpenCue/rqd.conf')
else:
    CONFIG_FILE = '/etc/opencue/rqd.conf'

# Then overwrites with an eventual shared configuration file
CONFIG_FILE = os.environ.get('RQD_CONFIG_FILE', CONFIG_FILE)

# Finally get the one passed as argument when launching rqd
if '-c' in sys.argv:
    CONFIG_FILE = sys.argv[sys.argv.index('-c') + 1]

OVERRIDE_CORES = None # number of cores. ex: None or 8
OVERRIDE_IS_DESKTOP = None # Force rqd to run in 'desktop' mode
OVERRIDE_PROCS = None # number of physical cpus. ex: None or 2
OVERRIDE_MEMORY = None # in Kb
OVERRIDE_NIMBY = None # True to turn on, False to turn off
USE_NIMBY_PYNPUT = True # True pynput, False select
OVERRIDE_HOSTNAME = None # Force to use this hostname
ALLOW_GPU = False
LOAD_MODIFIER = 0 # amount to add/subtract from load

LOG_FORMAT = '%(levelname)-9s openrqd-%(module)-10s: %(message)s'
CONSOLE_LOG_LEVEL = logging.WARNING
# Equal to or greater than the consoleLevel. None deactives logging to file
FILE_LOG_LEVEL = None

if subprocess.getoutput('/bin/su --help').find('session-command') != -1:
    SU_ARGUMENT = '--session-command'
else:
    SU_ARGUMENT = '-c'

SP_OS = platform.system()

# Docker mode config
DOCKER_AGENT = None
DOCKER_GPU_MODE = False

# Backup running frames cache. Backup cache is turned off if this path is set to
# None or ""
BACKUP_CACHE_PATH = ""
BACKUP_CACHE_TIME_TO_LIVE_SECONDS = 60

try:
    if os.path.isfile(CONFIG_FILE):
        # Hostname can come from here: rqutil.getHostname()
        __override_section = "Override"
        __host_env_var_section = "UseHostEnvVar"

        # Directly use RawConfigParser from configparser
        ConfigParser = configparser.RawConfigParser

        # Allow some config file sections to contain only keys
        config = ConfigParser(allow_no_value=True)
        # Respect case from the config file keys
        config.optionxform = str
        config.read(CONFIG_FILE)
        logging.warning('Loading config %s', CONFIG_FILE)

        if config.has_option(__override_section, "RQD_GRPC_PORT"):
            RQD_GRPC_PORT = config.getint(__override_section, "RQD_GRPC_PORT")
        if config.has_option(__override_section, "CUEBOT_GRPC_PORT"):
            CUEBOT_GRPC_PORT = config.getint(__override_section, "CUEBOT_GRPC_PORT")
        if config.has_option(__override_section, "OVERRIDE_CORES"):
            OVERRIDE_CORES = config.getint(__override_section, "OVERRIDE_CORES")
        if config.has_option(__override_section, "OVERRIDE_PROCS"):
            OVERRIDE_PROCS = config.getint(__override_section, "OVERRIDE_PROCS")
        if config.has_option(__override_section, "OVERRIDE_MEMORY"):
            OVERRIDE_MEMORY = config.getint(__override_section, "OVERRIDE_MEMORY")
        if config.has_option(__override_section, "OVERRIDE_CUEBOT"):
            CUEBOT_HOSTNAME = config.get(__override_section, "OVERRIDE_CUEBOT")
        if config.has_option(__override_section, "OVERRIDE_NIMBY"):
            OVERRIDE_NIMBY = config.getboolean(__override_section, "OVERRIDE_NIMBY")
        if config.has_option(__override_section, "USE_NIMBY_PYNPUT"):
            USE_NIMBY_PYNPUT = config.getboolean(__override_section, "USE_NIMBY_PYNPUT")
        if config.has_option(__override_section, "OVERRIDE_IS_DESKTOP"):
            OVERRIDE_IS_DESKTOP = config.getboolean(__override_section, "OVERRIDE_IS_DESKTOP")
        if config.has_option(__override_section, "OVERRIDE_HOSTNAME"):
            OVERRIDE_HOSTNAME = config.get(__override_section, "OVERRIDE_HOSTNAME")
        if config.has_option(__override_section, "GPU"):
            ALLOW_GPU = config.getboolean(__override_section, "GPU")
        if config.has_option(__override_section, "LOAD_MODIFIER"):
            LOAD_MODIFIER = config.getint(__override_section, "LOAD_MODIFIER")
        if config.has_option(__override_section, "RQD_USE_IP_AS_HOSTNAME"):
            RQD_USE_IP_AS_HOSTNAME = config.getboolean(__override_section, "RQD_USE_IP_AS_HOSTNAME")
        if config.has_option(__override_section, "RQD_USE_IPV6_AS_HOSTNAME"):
            RQD_USE_IPV6_AS_HOSTNAME = config.getboolean(__override_section,
                                                         "RQD_USE_IPV6_AS_HOSTNAME")
        if config.has_option(__override_section, "RQD_USE_PATH_ENV_VAR"):
            RQD_USE_PATH_ENV_VAR = config.getboolean(__override_section, "RQD_USE_PATH_ENV_VAR")
        if config.has_option(__override_section, "RQD_USE_ALL_HOST_ENV_VARS"):
            RQD_USE_HOST_ENV_VARS = config.getboolean(__override_section,
                "RQD_USE_ALL_HOST_ENV_VARS")
        if config.has_option(__override_section, "RQD_BECOME_JOB_USER"):
            RQD_BECOME_JOB_USER = config.getboolean(__override_section, "RQD_BECOME_JOB_USER")
        if config.has_option(__override_section, "RQD_TAGS"):
            RQD_TAGS = config.get(__override_section, "RQD_TAGS")
        if config.has_option(__override_section, "DEFAULT_FACILITY"):
            DEFAULT_FACILITY = config.get(__override_section, "DEFAULT_FACILITY")
        if config.has_option(__override_section, "LAUNCH_FRAME_USER_GID"):
            LAUNCH_FRAME_USER_GID = config.getint(__override_section, "LAUNCH_FRAME_USER_GID")
        if config.has_option(__override_section, "CONSOLE_LOG_LEVEL"):
            level = config.get(__override_section, "CONSOLE_LOG_LEVEL")
            CONSOLE_LOG_LEVEL = logging.getLevelName(level)
        if config.has_option(__override_section, "FILE_LOG_LEVEL"):
            level = config.get(__override_section, "FILE_LOG_LEVEL")
            FILE_LOG_LEVEL = logging.getLevelName(level)
        if config.has_option(__override_section, "RQD_PREPEND_TIMESTAMP"):
            RQD_PREPEND_TIMESTAMP = config.getboolean(__override_section, "RQD_PREPEND_TIMESTAMP")
        if config.has_option(__override_section, "CHECK_INTERVAL_LOCKED"):
            CHECK_INTERVAL_LOCKED = config.getint(__override_section, "CHECK_INTERVAL_LOCKED")
        if config.has_option(__override_section, "MINIMUM_IDLE"):
            MINIMUM_IDLE = config.getint(__override_section, "MINIMUM_IDLE")
        if config.has_option(__override_section, "SENTRY_DSN_PATH"):
            SENTRY_DSN_PATH = config.getint(__override_section, "SENTRY_DSN_PATH")
        if config.has_option(__override_section, "SP_OS"):
            SP_OS = config.get(__override_section, "SP_OS")
        if config.has_option(__override_section, "RQD_CUSTOM_HOME_PREFIX"):
            RQD_CUSTOM_HOME_PREFIX = config.get(__override_section, "RQD_CUSTOM_HOME_PREFIX")
        if config.has_option(__override_section, "RQD_CUSTOM_MAIL_PREFIX"):
            RQD_CUSTOM_MAIL_PREFIX = config.get(__override_section, "RQD_CUSTOM_MAIL_PREFIX")

        if config.has_section(__host_env_var_section):
            RQD_HOST_ENV_VARS = config.options(__host_env_var_section)

        if config.has_option(__override_section, "BACKUP_CACHE_PATH"):
            BACKUP_CACHE_PATH = config.get(__override_section, "BACKUP_CACHE_PATH")
        if config.has_option(__override_section, "BACKUP_CACHE_TIME_TO_LIVE_SECONDS"):
            BACKUP_CACHE_TIME_TO_LIVE_SECONDS = config.getint(
                __override_section, "BACKUP_CACHE_TIME_TO_LIVE_SECONDS")

        if config.has_option(__override_section, "RQD_DISPLAY_PATH"):
            RQD_DISPLAY_PATH = config.get(__override_section, "RQD_DISPLAY_PATH")


        __docker_config = "docker.config"
        __docker_gpu_mode = "DOCKER_GPU_MODE"

        if config.has_section(__docker_config):
            if config.getboolean(__docker_config, "RUN_ON_DOCKER"):
                from rqd.rqdocker import RqDocker

                # Set config attribute for docker_gpu_mode. Configuration is made available
                # from both the config file and an environment variable, the latter takes precedence
                if __docker_gpu_mode in os.environ:
                    config[__docker_config][__docker_gpu_mode] = os.environ[__docker_gpu_mode]

                DOCKER_AGENT = RqDocker.fromConfig(config)
                # rqd needs to run as root to be able to run docker
                RQD_UID = 0
                RQD_GID = 0

                # Make sure sp_os is updated with the versions configured on DOCKER_AGENT
                SP_OS = DOCKER_AGENT.sp_os

# pylint: disable=broad-except
except Exception as e:
    logging.warning(
        "Failed to read values from config file %s due to %s at %s",
        CONFIG_FILE, e, traceback.extract_tb(sys.exc_info()[2]))

logging.warning("CUEBOT_HOSTNAME: %s", CUEBOT_HOSTNAME)
