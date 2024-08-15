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
Classes responsible for setting up an outline.versions session.
"""

from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import atexit
from builtins import str
from builtins import object
import logging
import os
import shutil
import sys
import tempfile

from future.utils import with_metaclass


logger = logging.getLogger("versions")


class Settings(object):
    """
    Local session settings.
    """
    # Path containing different outline library versions
    repos_path = ""
    module_repos = {}


class Singleton(type):
    """
    Basic singleton implementation.
    """
    # pylint: disable=super-init-not-called
    def __init__(cls, name, bases, namespace):
        cls._obj = type(name, bases, namespace)()
        atexit.register(cls._obj.clean, shutil_ptr=shutil)

    def __call__(cls):
        return cls._obj


class Session(with_metaclass(Singleton, object)):
    """
    The Session class handles creation of the versioning session.
    """

    # pylint: disable=non-parent-init-called
    def __init__(self):
        object.__init__(self)
        self.__modules = {}
        self.__create_path()

    def require(self, module, version):
        """Symlinks a module into the session's temp dir."""

        # Bail out if we've already loaded the module.
        if self.is_module_loaded(module):
            if str(version) != self.__modules[module]:
                logger.warning(
                    "Can't load %s-%s, version %s is already loaded.",
                    module,
                    version,
                    self.__modules[module])
            return False

        if not Settings.module_repos and not Settings.repos_path:
            logger.warning("No repo paths were configured, not requiring a version.")
            return False

        # Find the destination.
        if module in Settings.module_repos:
            src = os.path.join(Settings.module_repos[module],
                               module, version)
        else:
            src = os.path.join(Settings.repos_path, module, version)

        src = os.path.realpath(src)

        # Resolve the new version.  Only use the resolved version if it
        # exists in the repos.
        hard_version = os.path.basename(src)
        if os.path.exists(os.path.join(Settings.repos_path, module, hard_version)):
            version = hard_version

        # Set the destination, this is the tmp python area.
        dst = "%s/%s" % (self.get_path(), module)

        # If the src dir doesn't exist in this repos, move on.
        if not os.path.exists(src):
            logger.warning("The source dir '%s' does not exist.", src)
            return False

        # Not a python module, so, we don't even add
        # it to the path, we just execute the
        # manifest if it exists.  Otherwise, we
        # link it into the repos.
        if os.path.exists("%s/__init__.py" % src):
            self.__link_version(src, dst)
            self.__lock_module(module, version)
            return True

        if os.path.exists("%s/manifest.py" % src):
            self.__run_manifest(src)
            self.__lock_module(module, version)
            return True

        logger.warning("Unable to load %s, not a module or manifest.", module)
        return False

    def unrequire(self, module):
        """
        Removes a module from the module list.
        """
        path = os.path.join(self.get_path(), module)
        if os.path.islink(path):
            try:
                del self.__modules[module]
                os.unlink(path)
                return True
            except KeyError:
                logger.warning("Module %s was not loaded.", module)
        else:
            logger.warning("Failed to remove symlink '%s', does not exist.", path)

        return False

    def is_module_loaded(self, name):
        """
        Return true if the given module is loaded.
        """
        return name in self.__modules

    def get_path(self):
        """Return the path to the session tmp dir."""
        return self.__path

    def clean(self, shutil_ptr):
        """
        Unloads all modules.

        :type shutil_ptr: shutil module
        :param shutil_ptr: reference to the shutil module. Only needed for Py2.7 compatibility.
        """
        self.__modules.clear()
        shutil_ptr.rmtree(self.get_path())

    def get_version(self, module, default="latest"):
        """
        Return the loaded version or default value if one
        is not loaded.
        """
        return self.__modules.get(module, default)

    def get_ver_str(self):
        """Gets a string representation of all loaded modules and their versions."""
        return ",".join(["%s:%s" % (mod, ver)
                         for mod, ver in self.__modules.items()])

    @staticmethod
    def __link_version(src, dst):
        os.symlink(src, dst)

    # pylint: disable=broad-except,import-outside-toplevel
    @staticmethod
    def __run_manifest(path):
        # pylint: disable=deprecated-module
        import imp
        try:
            fob, path, desc = imp.find_module('manifest', [path])
            imp.load_module("manifest", fob, path, desc)
            fob.close()
        except Exception as e:
            print("Failed to execute manifest file: %s" % e)

    def __lock_module(self, name, version):
        self.__modules[name] = str(version)

    def __create_path(self):
        self.__path = str(tempfile.mkdtemp())
        for num, path in enumerate(sys.path[1:]):
            if not path.startswith("/usr"):
                sys.path.insert(num + 1, self.__path)
                return
        sys.path.append(self.__path)
