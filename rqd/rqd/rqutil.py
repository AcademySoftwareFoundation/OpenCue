
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


"""Utility functions."""


from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

from builtins import str
from builtins import object
import functools
import logging
import os
import platform
import socket
import subprocess
import threading
import uuid
import psutil

import rqd.rqconstants

if platform.system() != 'Windows':
    import pwd
    import grp

    PERMISSIONS = threading.Lock()
    HIGH_PERMISSION_GROUPS = os.getgroups()
log = logging.getLogger(__name__)


class Memoize(object):
    """Decorator used to cache the results of functions that only need to be run once."""

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

    @staticmethod
    def isCached(cache, key):
        """Returns whether a given function has been cached already.

        Mocked in tests to disable caching as needed."""
        if key in cache:
            return True
        return False

    def cacheGet(self, cache, key, func):
        """Gets the cached result of a function."""
        if not self.isCached(cache, key):
            cache[key] = func()
        return cache[key]


def permissionsHigh():
    """Sets the effective gid/uid to processes original values (root)"""
    if platform.system() == "Windows" or not rqd.rqconstants.RQD_BECOME_JOB_USER:
        return
    # PERMISSIONS gets locked here and unlocked at permissionsLow()
    # therefore 'with' should not be used here
    # pylint: disable=consider-using-with
    PERMISSIONS.acquire()
    os.setegid(os.getgid())
    os.seteuid(os.getuid())
    try:
        os.setgroups(HIGH_PERMISSION_GROUPS)
    # pylint: disable=broad-except
    except Exception:
        pass


def permissionsLow():
    """Sets the effective gid/uid to one with less permissions:
       RQD_GID and RQD_UID"""
    if platform.system() in ('Windows', 'Darwin') or not rqd.rqconstants.RQD_BECOME_JOB_USER:
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
    if platform.system() in ('Windows', 'Darwin') or not rqd.rqconstants.RQD_BECOME_JOB_USER:
        return
    with PERMISSIONS:
        __becomeRoot()
        try:
            username = pwd.getpwuid(uid).pw_name
            groups = [20] + [g.gr_gid for g in grp.getgrall() if username in g.gr_mem]
            os.setgroups(groups)
        # pylint: disable=broad-except
        finally:
            os.setegid(gid)
            os.seteuid(uid)


def __becomeRoot():
    """Sets the effective gid/uid to the initial privileged settings"""
    if os.getegid() != os.getgid() or os.geteuid() != os.getuid():
        os.setegid(os.getgid())
        os.seteuid(os.getuid())
        try:
            os.setgroups(HIGH_PERMISSION_GROUPS)
        # pylint: disable=broad-except
        except Exception:
            pass


def checkAndCreateUser(username, uid=None, gid=None):
    """Check to see if the provided user exists, if not attempt to create it."""
    if platform.system() == "Windows" or not rqd.rqconstants.RQD_BECOME_JOB_USER:
        return
    try:
        pwd.getpwnam(username)
        return
    except KeyError:
        # Multiple processes can be trying to access passwd, permissionHigh and
        # permissionLow handle locking
        permissionsHigh()
        try:
            cmd = [
                'useradd',
                '-p', str(uuid.uuid4()),  # generate a random password
            ]
            if uid:
                cmd += ['-u', str(uid)]
            if gid:
                cmd += ['-g', str(gid)]
            cmd.append(username)
            log.info("Frame's username not found on host. Adding user with: %s", cmd)
            subprocess.check_call(cmd)
        # pylint: disable=broad-except
        except Exception:
            logging.info("useradd failed to add user: %s. User possibly already exists.", username)
        finally:
            permissionsLow()


def getInterfaceIp(interfaceName, ipv6=False):
    """Returns the IP for the given interface name.

    Requires the psutil library to be installed.

    :param interfaceName: name of the network interface
    :type interfaceName: str
    :param ipv6: True if you want an IPv6 address, False for IPv4
    :type ipv6: bool
    :return: IP address or None if not found
    :rtype: str
    """

    ipFamily = socket.AF_INET6 if ipv6 else socket.AF_INET
    interfaces = psutil.net_if_addrs()
    if interfaceName in interfaces:
        for interface in interfaces[interfaceName]:
            if interface.family == ipFamily:
                return interface.address
    log.warning('Interface %r with address family %s not found.', interfaceName, ipFamily)
    return None


def getHostIp():
    """Returns the machine's local ip address"""
    interfaceName = getattr(rqd.rqconstants, 'RQD_NETWORK_INTERFACE', None)
    if interfaceName:
        ip = getInterfaceIp(interfaceName, ipv6=rqd.rqconstants.RQD_USE_IPV6_AS_HOSTNAME)
        if ip:
            return ip
        log.warning(
            'Could not find IP for interface %r, falling back to hostname resolution.',
            interfaceName)

    if rqd.rqconstants.RQD_USE_IPV6_AS_HOSTNAME:
        return socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET6)[0][4][0]
    return socket.gethostbyname(socket.gethostname())


def getHostname():
    """Returns the machine's fully qualified domain name"""
    try:
        if rqd.rqconstants.OVERRIDE_HOSTNAME:
            return rqd.rqconstants.OVERRIDE_HOSTNAME
        if rqd.rqconstants.RQD_USE_IP_AS_HOSTNAME or rqd.rqconstants.RQD_USE_IPV6_AS_HOSTNAME:
            return getHostIp()
        return socket.gethostbyaddr(getHostIp())[0].split('.')[0]
    except (socket.herror, socket.gaierror):
        log.warning("Failed to resolve hostname to IP, falling back to local hostname")
        return socket.gethostname()


if __name__ == "__main__":
    pass
