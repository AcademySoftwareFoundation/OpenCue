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


"""Handle input and output."""


from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

from builtins import map
from builtins import str
from builtins import object
import os
import re
import logging
import shlex
import subprocess
import tempfile
import yaml

import FileSequence

from .exception import FileSpecException
from .exception import ShellCommandFailureException


logger = logging.getLogger("outline.io")

# Used to match version number in paths
VERSION_REGEX = re.compile(r'_v([\d+])')


def prep_shell_command(cmd, frame=None):
    """
    Prepare a shell command by ensuring that its
    an array, all elements are strings, and by replacing
    any frame range tokens.  Return the new shell command.
    """
    if not isinstance(cmd, (tuple, list, set)):
        cmd = shlex.split(str(cmd))

    has_range = "OL_LAYER_RANGE" in os.environ
    new_cmd = []
    for word in cmd:
        word = str(word)
        if frame:
            word = word.replace("%{FRAME}", "%s" % frame)
            word = word.replace("%{ZFRAME}", "%04d" % frame)
        if has_range:
            word = word.replace("%{RANGE}",
                                os.environ.get("OL_LAYER_RANGE"))
        new_cmd.append(word)
    return new_cmd


def system(cmd, ignore_error=False, frame=None):
    """
    Shell out to the given command and wait for it to finish.

    :type  cmd: list<str>
    :param cmd: The command to execute.

    :type ignore_error: boolean
    :param ignore_error: Ignore any L{OSError} or shell command failures.
    """
    cmd = prep_shell_command(cmd, frame)
    str_cmd = " ".join(map(str, cmd))

    try:
        logger.info("About to run: %s", str_cmd)
        retcode = subprocess.call(cmd, shell=False)
        if retcode != 0 and not ignore_error:
            msg = "shell out to '%s' failed, exit status %d" % (str_cmd, retcode)
            logger.critical(msg)
            raise ShellCommandFailureException(msg, retcode)
    except OSError as oserr:
        msg = "shell out to '%s' failed, msg %s errno %d" % (str_cmd,
                                                             oserr.strerror,
                                                             oserr.errno)
        logger.critical(msg)
        raise ShellCommandFailureException(msg, 16)


def resolve(path):
    """
    Resolve a realtive path or shot tree URI to a full path.

    :rtype: str
    :return: the full path
    """
    path = str(path)

    return path


class Path(object):
    """
    Any non-image shot tree path, trunk, or branch.

    Depending on the type of file that Path represents, iterating
    over this object will do one of three things.

       - file - iterates over the single path.
       - dir - iterates over all files in the directory.
       - unknown/non-exist - throw IOException

    """
    def __init__(self, path, **args):
        object.__init__(self)
        self.__path = resolve(str(path))

        self.__attributes = {}
        self.__attributes["checked"] = False
        self.__attributes["mkdir"] = False
        self.__attributes.update(args)

    def get_attribute(self, name, default=None):
        """
        Get a named attribute from the given name.
        """
        return self.__attributes.get(name, default)

    def set_attribute(self, name, value):
        """
        Set a named attribute to the name/value.
        """
        self.__attributes[name] = value

    def get_attributes(self):
        """
        Return a copy of the attribute map.
        """
        return dict(self.__attributes)

    def mkdir(self):
        """
        Create the path
        """
        os.mkdir(self.__path)

    def exists(self, frame_set=None):
        """
        Return true if the path exists.

        :rtype: boolean
        :return: true if path exists.
        """
        # frame_set isn't used here, but child classes need it, so we keep it here to keep
        # args consistent
        del frame_set

        return os.path.exists(self.__path)

    def get_basename(self):
        """
        Return the file's base name.

        :rtype: string
        :return: the base name of the path.
        """
        return os.path.basename(self.__path)

    def get_dirname(self):
        """
        Return the file's directory.  If the path is a
        directory, it retrns itself.

        :rtype: string
        :return: the full path to the directory
        """
        if os.path.isdir(self.__path):
            return self.__path
        return os.path.dirname(self.__path)

    def get_ext(self):
        """
        Return the file extention.

        :rtype:  string
        :return: the file extension.
        """
        return os.path.splitext(self.__path)[1]

    def get_path(self):
        """
        Return the full path.

        :rtype: string
        :return: full path to this file
        """
        return self.__path

    def get_size(self, frame_set=None):
        """
        Return the size of the file or path.
        """
        # frame_set isn't used here, but child classes need it, so we keep it here to keep
        # args consistent
        del frame_set

        return os.path.getsize(self.__path)

    def __str__(self):
        return self.get_path()

    def __eq__(self, other):
        return str(self) == str(other)


class FileSpec(Path):
    """
    A path to an image or sequence of images.  Path must be a
    standard image path.
    """

    # pylint: disable=no-member
    def __init__(self, path, **args):
        Path.__init__(self, path, **args)
        try:
            self.__fs = FileSequence.FileSequence(self.get_path())
        except ValueError as e:
            logger.critical("Failed to parse spec: %s.", self.get_path())
            raise e

        if "mkdir" not in args:
            self.set_attribute("mkdir", False)

    def exists(self, frame_set=None):
        """
        Return true if the image or all images in
        the sequence exist.

        :rtype:  boolean
        :return: true if image(s) exist
        """
        def exists(path):
            logger.info("checking for existance of path: %s", path)
            if not os.path.exists(path):
                return False
            if os.path.getsize(path) == 0:
                return False
            return True

        if frame_set:
            for f in frame_set:
                path = self.get_frame_path(f)
                if not exists(path):
                    for ext in self.get_attribute("checkExt", []):
                        n = path[0:path.rfind(self.get_ext())]
                        n = "%s%s" % (n, ext)
                        if exists(n):
                            return True
                    return False
        else:
            for path in self.__fs:
                if not exists(path):
                    for ext in self.get_attribute("checkExt", []):
                        n = path[0:path.rfind(self.get_ext())]
                        n = "%s%s" % (n, ext)
                        if exists(n):
                            return True
                    return False
        return True

    def get_size(self, frame_set=None):
        """
        Return the size of the file or path.
        """
        size = 0
        if frame_set:
            for f in frame_set:
                path = self.get_frame_path(f)
                try:
                    size += os.path.getsize(path)
                except OSError as e:
                    logger.warning("Failed to find the size of: %s, %s", path, e)
        else:
            for path in self.__fs:
                try:
                    size += os.path.getsize(path)
                except OSError as e:
                    logger.warning("Failed to find the size of: %s, %s", path, e)

        return size

    def get_basename(self):
        """
        Return the base name of the image.  The
        basename does not include the frame range
        or file extension.

        :rtype:  string
        :return: the base name of the image
        """
        return self.__fs.getBasename()

    def get_dirname(self):
        """
        Return the path to the directory for this image.

        :rtype:  string
        :return: the full directory path
        """
        return self.__fs.getDirname()[0:-1]

    def get_ext(self):
        """
        Return the file extention.

        :rtype:  string
        :return: the file extension.
        """
        return self.__fs.getSuffix()

    def get_colorspace(self):
        """
        Return the color space.

        :rtype:  string
        :return: the image color space
        """
        rep = self.get_rep().split("_")
        if len(rep) in (2,3):
            cs = rep[1]
        else:
            cs = rep[-2]
        return cs

    def get_res(self):
        """
        Return the resolution data for this image.

        :rtype:  ResolutionTableEntry
        :return: The resolution table entry.
        """
        rep = self.get_rep().split("_")
        if len(rep) in (2,3):
            res = rep[0]
        else:
            try:
                res = rep[-3]
            except IndexError as e:
                res = None
                msg = "Unable to find valid resolution: %s, %s" % (rep, e)
                raise FileSpecException(msg)

        return res

    def get_rep(self):
        """
        Return the representation.  The representation is
        the oav_resolution_colorspace.

        :rtype:  string
        :return: the representation.
        """
        return self.__fs.getDirname().rsplit("/", 2)[1]

    def get_element_dir(self):
        """
        Return the element directory path.

        :rtype:  string
        :return: the element directory.
        """
        return self.__fs.getDirname().rsplit("/", 2)[0] + "/"

    def get_frame_path(self, num):
        """
        Return the path to a particular frame of this FileSpec.

        :rtype: FrameSet
        :return: A path to an individual frame with this file spec.
        """
        return self.__fs(num)

    def get_temp_frame_path(self, num, path=None):
        """
        Return the path to a particular frame of this Filespec
        in a temporary location.  Optionally provide a bash path
        for the temporary file.
        """
        return "%s/%s" % (path or tempfile.gettempdir(),
                          os.path.basename(self.get_frame_path(num)))

    def get_temp_file_spec(self, path=None):
        """
        Return a path to the the file spec in a temporary location
        or a supplied path.
        """
        return "%s/%s" % (path or tempfile.gettempdir(),
                          os.path.basename(self.get_file_spec()))

    def get_frame_set(self):
        """
        Return the sequence's frame set object.

        :rtype: FrameSet
        :return: The current framet set.
        """
        return FileSequence.FrameSet(str(self.__fs.frameSet))

    def get_file_spec(self, fs=None):
        """
        Return the base file specification.  By default, the
        result has no frame range.  If the fs argument is specified,
        the result will contain a frame range.

        :rtype: str
        :return: A file spec.
        """
        e = self.get_path().split(".")
        if fs:
            e[-2] = fs
        else:
            e[-2] = "#"

        return ".".join(e)


def file_spec_serializer(dumper, data):
    """
    Serialize a FileSpec object.  This is required for Yaml
    to serialize a FileSpec properly.
    """
    return dumper.represent_scalar('!FileSpec',
                                   '%s' % yaml.dump([data.get_path(),
                                                     data.get_attributes()]))


def file_spec_constructor(loader, node):
    """
    Unserializes a yamlized FileSpec.
    """
    value = yaml.load(loader.construct_scalar(node), Loader=yaml.Loader)
    return FileSpec(value[0], **value[1])


# Register the yaml serialize/unserialize callbacks.
yaml.add_representer(FileSpec, file_spec_serializer)
yaml.add_constructor('!FileSpec', file_spec_constructor)
