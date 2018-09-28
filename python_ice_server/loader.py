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



# $HeadURL$
# $LastChangedDate$
# $LastChangedBy$
# $LastChangedRevision$

import os
import sys

def __setup_python_for_ice(version):
    """Set up Python to use Ice 3.3.x, which lives in a Imageworks'
    specific directory for the Imageworks' Linux systems.  If this is
    not done, then either Ice will not be found if the old 3.1.1
    ice*rpm RPMs are not installed or Ice 3.1.1 will be used.  The
    following needs to be done:
    1) Prepend to Python's module search path to use the Ice 3.3.x
       directory.
    2) Add the Ice bin directory to the path, since Python's dynamic
       Slice loading uses icecpp.

    Return the path to the top level directory of the Ice
    installation.
    """

    # For rhel7
    if os.path.isfile("/usr/lib64/python2.7/site-packages/Ice/Ice.py"):
        return "/usr"

    # For Spinux
    if os.path.isfile("/usr/lib64/python2.6/site-packages/Ice.py"):
        return "/usr"

    # For Fedora
    if os.path.isfile("/usr/lib64/python2.6/site-packages/Ice/Ice.py"):
        return "/usr"

    # For Debian
    if os.path.isfile("/usr/local/lib/python2.7/dist-packages/Ice/__init__.py"):
        return "/usr"

    import platform

    platform_name = platform.system()

    if platform_name == 'Windows':
        ice_dirs = ['C:\Program Files\ZeroC\Ice-3.4.0']
        for ice_dir in ice_dirs:
            if os.path.isdir(ice_dir):
                return ice_dir

        raise RuntimeError("No IcePy installations found in '%s'." % ice_dir)

    if platform_name == 'Darwin':
        ice_dirs = ['/opt/local-2009-12/share/ice', '/opt/local', '/opt/local-development']
        for ice_dir in ice_dirs:
            if os.path.isdir(ice_dir):
                return ice_dir

        raise RuntimeError("No IcePy installations found in '%s'." % ice_dir)

    import struct

    # The location of the Ice Python bindings depend upon the version
    # of Python and if the Python process is a 32-bit or a 64-bit
    # process.  An 64-bit system can run a 32-bit Python process, so
    # checking the system's uname is not correct.  Instead, check if
    # the length of an integer wide enough to hold a pointer is 4 or 8
    # bytes long.

    # The root directory for all Ice versions depends upon a 32- or
    # 64-bit Python.
    if struct.calcsize('P') == 8:
        ice_dir = '/usr/local64/ice'
    else:
        ice_dir = '/usr/local/ice'

    # Find the first gcc version that exists with Python bindings.
    try:
        gcc_versions = [d for d in os.listdir(ice_dir)
                        if d.startswith('%s-gcc' % version)]
    except OSError:
        # Likely ice_dir does not exist.
        raise RuntimeError("No IcePy installations found in '%s'." % ice_dir)

    gcc_versions.sort()

    for gcc_version in gcc_versions:
        ice_home = os.path.join(ice_dir, gcc_version)
        python_path = os.path.join(ice_home,
                                   'lib',
                                   'python%s.%s' % sys.version_info[0:2])
        if os.path.isdir(python_path):
            if not python_path in sys.path:
                sys.path.insert(0, python_path)
            path = os.getenv('PATH')
            ice_bin_dir = os.path.join(ice_home, 'bin')
            if path:
                path = '%s:%s' % (ice_bin_dir, path)
            else:
                path = ice_bin_dir
            os.putenv('PATH', path)
            return ice_home

    raise RuntimeError("No IcePy installations found in '%s'." % ice_dir)

def setup_python_for_ice_3_2():
    """Set up Python's sys.path to be able to load the Ice 3.2 Python
    bindings on a Sony Pictures Imageworks system.  Return the path to the
    top level directory of the Ice installation.  Raise RuntimeError if no
    IcePy installation is found."""

    return __setup_python_for_ice('3.2')

def setup_python_for_ice_3_3():
    """Set up Python's sys.path to be able to load the Ice 3.3 Python
    bindings on a Sony Pictures Imageworks system.  Return the path to the
    top level directory of the Ice installation.  Raise RuntimeError if no
    IcePy installation is found."""

    return __setup_python_for_ice('3.3')

