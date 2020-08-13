
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
Utility functions.
"""


from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

from builtins import str
from builtins import object
import functools
import logging as log
import os
import platform
import random
import socket
import subprocess
import threading
import uuid

import rqd.rqconstants

if platform.system() != 'Windows':
    import pwd
    import grp

    PERMISSIONS = threading.Lock()
    HIGH_PERMISSION_GROUPS = os.getgroups()


class Memoize(object):
    def __init__(self, func):
        self.func = func
        self.memoized = {}
        self.methodCache = {}

    def __call__(self, *args):
        return self.cacheGet(
            self.memoized, args, lambda: self.func(*args))

    def __get__(self, obj, objtype):
        return self.cacheGet(
            self.methodCache, obj, lambda: self.__class__(functools.partial(self.func, obj)))

    def isCached(self, cache, key):
        """Mocked in tests to disable caching as needed."""
        if key in cache:
            return True
        return False

    def cacheGet(self, cache, key, func):
        if not self.isCached(cache, key):
            cache[key] = func()
        return cache[key]


def permissionsHigh():
    """Sets the effective gid/uid to processes original values (root)"""
    if platform.system() == "Windows":
        return
    PERMISSIONS.acquire()
    os.setegid(os.getgid())
    os.seteuid(os.getuid())
    try:
        os.setgroups(HIGH_PERMISSION_GROUPS)
    except Exception:
        pass


def permissionsLow():
    """Sets the effective gid/uid to one with less permissions:
       RQD_GID and RQD_UID"""
    if platform.system() in ('Windows', 'Darwin'):
        return
    if os.getegid() != rqd.rqconstants.RQD_GID or os.geteuid() != rqd.rqconstants.RQD_UID:
        __becomeRoot()
        os.setegid(rqd.rqconstants.RQD_GID)
        os.seteuid(rqd.rqconstants.RQD_UID)
    # This will be skipped on first start
    if PERMISSIONS.locked():
        PERMISSIONS.release()


def permissionsUser(uid, gid):
    """Sets the effective gid/uid to supplied values"""
    if platform.system() in ('Windows', 'Darwin'):
        return
    PERMISSIONS.acquire()
    __becomeRoot()
    try:
        username = pwd.getpwuid(uid).pw_name
        groups = [20] + [g.gr_gid for g in grp.getgrall() if username in g.gr_mem]
        os.setgroups(groups)
    except Exception:
        pass
    os.setegid(gid)
    os.seteuid(uid)


def __becomeRoot():
    """Sets the effective gid/uid to the initial privileged settings"""
    if os.getegid() != os.getgid() or os.geteuid() != os.getuid():
        os.setegid(os.getgid())
        os.seteuid(os.getuid())
        try:
            os.setgroups(HIGH_PERMISSION_GROUPS)
        except Exception:
            pass


def checkAndCreateUser(username):
    """Check to see if the provided user exists, if not attempt to create it."""
    # TODO(gregdenton): Add Windows and Mac support here. (Issue #61)
    try:
        pwd.getpwnam(username)
        return
    except KeyError:
        subprocess.check_call([
            'useradd',
            '-p', str(uuid.uuid4()), # generate a random password
            username
        ])


def getHostIp():
    """Returns the machine's local ip address"""
    return socket.gethostbyname(socket.gethostname())


def getHostname():
    """Returns the machine's fully qualified domain name"""
    try:
        if rqd.rqconstants.RQD_USE_IP_AS_HOSTNAME:
            return getHostIp()
        else:
            return socket.gethostbyaddr(socket.gethostname())[0].split('.')[0]
    except (socket.herror, socket.gaierror):
        log.warning("Failed to resolve hostname to IP, falling back to local hostname")
        return socket.gethostname()


if __name__ == "__main__":
    pass
