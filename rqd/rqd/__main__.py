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


def reopen_stdout_stderr(log_path):
    """
    Flush sys.stdout and sys.stderr and then reopen the underlying
    file descriptor for both stdout and stderr to the file at
    LOG_PATH.  LOG_PATH is opened before stdout and stderr are closed,
    so if LOG_PATH fails to open, stdout and stderr will remain
    unchanged.
    """
    log_fd = os.open(log_path, os.O_CREAT|os.O_WRONLY|os.O_TRUNC, 0o644)

    for f in [sys.stdout, sys.stderr]:
        fileno = f.fileno()
        f.flush()
        os.close(fileno)
        os.dup2(log_fd, fileno)

    os.close(log_fd)


def daemonize(log_path=None, chdir_to_root=True):
    """
    Daemonizes the current process. The process will be in a new session
    with stdin reading from /dev/null and stdout and stderr writing to
    /dev/null with all other file descriptors closed.

    :type log_path: String
    :param log_path: If LOG_PATH is provided, then stdout and stderr
                     write to LOG_PATH. LOG_PATH may be a relative
                     path to the process' current working directory
                     before calling daemonize().
    :type chdir_to_root: bool
    :param chdir_to_root: If CHDIR_TO_ROOT is True, then the process'
                          current working directory will be changed
                          to / after opening the log files; if
                          CHDIR_TO_ROOT is false, then the current
                          working directory is not changed.
    """
    # pylint: disable=import-outside-toplevel
    import resource

    if hasattr(os, "devnull"):
        dev_null = os.devnull
    else:
        dev_null = "/dev/null"

    if not log_path:
        log_path = dev_null

    # pylint: disable=protected-access
    if os.fork() != 0:
        # Intentionally not using sys.exit here to avoid raising SystemExit,
        # cleaning handlers and flushing stdio buffers
        os._exit(0)

    os.setsid()

    if os.fork() != 0:
        # Intentionally not using sys.exit here to avoid raising SystemExit,
        # cleaning handlers and flushing stdio buffers
        os._exit(0)
    # pylint: enable=protected-access

    os.close(sys.stdin.fileno())
    os.open(dev_null, os.O_RDONLY)

    # The log file is opened before chdir'ing so a relative path may
    # be used and is opened before stdout and stderr are closed so any
    # errors in opening it will appear on stderr.
    reopen_stdout_stderr(log_path)

    if chdir_to_root:
        os.chdir('/')

    max_fd = resource.getrlimit(resource.RLIMIT_NOFILE)[1]
    if max_fd == resource.RLIM_INFINITY:
        max_fd = 1024
    for fd in range(3, max_fd+1):
        try:
            # Ice.loadSlice() function sometimes open /dev/urandom to
            # get random numbers. If daemonize() function is called after
            # Ice.loadSlice(), we should not close /dev/urandom. Or else
            # the child process will get exceptions when trying to access
            # /dev/urandom.
            fn = os.readlink("/proc/%s/%s" % (os.getpid(), fd))
            if fn != "/dev/urandom":
                os.close(fd)
        except OSError:
            pass

def setupLogging():
    """Sets up the logging for RQD.
    Logs to /var/log/messages"""
    logger = logging.getLogger()
    logger.setLevel(rqd.rqconstants.CONSOLE_LOG_LEVEL)
    for handler in logger.handlers:
        handler.setFormatter(logging.Formatter(rqd.rqconstants.LOG_FORMAT))

    if rqd.rqconstants.FILE_LOG_LEVEL is not None:
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
        logger.addHandler(logfile)


def setup_sentry():
    """Set up sentry if a SENTRY_DSN_PATH is configured"""
    sentry_dsn_path = rqd.rqconstants.SENTRY_DSN_PATH
    if sentry_dsn_path is None:
        return

    # Not importing sentry at the toplevel to avoid an unecessary dependency
    try:
        # pylint: disable=import-outside-toplevel
        import sentry_sdk
        # pylint: enable=import-outside-toplevel
        sentry_sdk.init(sentry_dsn_path)
    except ImportError:
        logging.warning('Sentry support disabled. SENTRY_DSN_PATH is set but '
                        'the lib is not available')


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
    logger = logging.getLogger()

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
        if option in ["-d", "--daemon"] and platform.system() != "Windows":
            daemonize()
        if option in ["--nimbyoff"]:
            optNimbyOff = True

    rqd.rqutil.permissionsLow()

    logger.warning('RQD Starting Up')

    setup_sentry()

    rqCore = rqd.rqcore.RqCore(optNimbyOff)
    rqCore.start()


if __name__ == "__main__":
    main()
