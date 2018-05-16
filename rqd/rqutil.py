
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
Utility functions.

Project: RQD

Module: rqutil.py

Contact: Middle-Tier (middle-tier@imageworks.com)

SVN: $Id$
"""
import os
import sys
import grp
import pwd
import threading
import platform
import socket
import functools

import rqconstants

PERMISSIONS = threading.Lock()
HIGH_PERMISSION_GROUPS = os.getgroups()

class Memoize(object):
    """From: https://gist.github.com/267733/8f5d2e3576b6a6f221f6fb7e2e10d395ad7303f9"""
    def __init__(self, func):
        self.func = func
        self.memoized = {}
        self.method_cache = {}
    def __call__(self, *args):
        return self.cache_get(self.memoized, args,
            lambda: self.func(*args))
    def __get__(self, obj, objtype):
        return self.cache_get(self.method_cache, obj,
            lambda: self.__class__(functools.partial(self.func, obj)))
    def cache_get(self, cache, key, func):
        try:
            return cache[key]
        except KeyError:
            result = func()
            cache[key] = result
            return result

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
    if platform.system() == 'Windows':
        return
    if os.getegid() != rqconstants.RQD_GID or os.getegid() != rqconstants.RQD_GID:
        __becomeRoot()
        os.setegid(rqconstants.RQD_GID)
        os.seteuid(rqconstants.RQD_UID)
    # This will be skipped on first start
    if PERMISSIONS.locked():
        PERMISSIONS.release()

def permissionsUser(uid, gid):
    """Sets the effective gid/uid to supplied values"""
    if platform.system() == 'Windows':
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
    if os.getegid() != os.getgid() or os.getegid() != os.getuid():
        os.setegid(os.getgid())
        os.seteuid(os.getuid())
        try:
            os.setgroups(HIGH_PERMISSION_GROUPS)
        except Exception:
            pass

def getHostname():
    """Returns the machine's fully qualified domain name"""
    if platform.system() == "Linux":
        # This may not work in windows/mac, need to test
        return socket.gethostbyaddr(socket.gethostname())[0]
    else:
        return socket.gethostname()

if __name__ == "__main__":
    pass

