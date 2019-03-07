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


import os
import shutil
import sys
import atexit
import tempfile
import logging

logger = logging.getLogger("versions")

class Settings:
    # Path containing different outline library versions
    repos_path = ""
    module_repos = { }

class Singleton:
    def __init__(self, name, bases, namespace):
        self._obj=type(name,bases,namespace)()
        atexit.register(self._obj.clean)

    def __call__(self):
        return self._obj

class Session(object):

    __metaclass__ = Singleton

    """
    The Session class handles creation of the versioning session.
    """
    def __init__(self):
        object.__init__(self)
        self.__modules = { }
        self.__create_path()

    def require(self, module, version, force=False):
        """Symlinks a module into the session's temp dir."""

        # Bail out if we've already loaded the module.
        if self.is_module_loaded(module):
            if str(version) != self.__modules[module]:
                logger.warn("Can't load %s-%s, version %s is already loaded."
                            % (module, version, self.__modules[module]))
            return False

        # Find the destination.
        if Settings.module_repos.has_key(module):
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
            logger.warn("The source dir '%s' does not exist." % src)
            return False

        # Not a python module, so, we don't even add
        # it to the path, we just execute the
        # manifest if it exists.  Otherwise, we
        # link it into the repos.
        if os.path.exists("%s/__init__.py" % src):
            self.__link_version(src, dst, version)
            self.__lock_module(module, version)
            return True
        elif os.path.exists("%s/manifest.py" % src):
            self.__run_manifest(src, version)
            self.__lock_module(module, version)
            return True
        else:
            logger.warn("Unabled to load %s, not a module or manifest." % module)

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
            except KeyError, kerr:
                logger.warn("Module %s was not loaded." % module)
        else:
            logger.warn("Failed to remove symlink '%s', does not exist." % path)
        return False

    def is_module_loaded(self, name):
        """
        Return true if the given module is loaded.
        """
        return self.__modules.has_key(name)

    def get_path(self):
        """Return the path to the session tmp dir."""
        return self.__path

    def clean(self):
        """
        Unloads all modules.
        """
        self.__modules.clear()
        shutil.rmtree(self.get_path())

    def get_version(self, module, default="latest"):
        """
        Return the loaded version or default value if one
        is not loaded.
        """
        return self.__modules.get(module, default)

    def get_ver_str(self):
        return ",".join(["%s:%s" % (mod, ver)
                         for mod, ver in self.__modules.iteritems()])

    def __link_version(self, src, dst, version):
        os.symlink(src, dst)

    def __run_manifest(self, path, version):
        import imp
        try:
            fob, path, desc = imp.find_module('manifest', [path])
            mob = imp.load_module("manifest", fob, path, desc)
            fob.close()
        except Exception, e:
            print "Failed to execute manifest file: %s" % e

    def __lock_module(self, name, version):
        self.__modules[name] = str(version)

    def __create_path(self):
        self.__path = str(tempfile.mkdtemp())
        for num, path in enumerate(sys.path[1:]):
            if not path.startswith("/usr"):
                sys.path.insert(num + 1, self.__path)
                return
        sys.path.append(self.__path)
