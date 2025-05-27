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


"""Global storage and data exchange."""


from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

from builtins import str
from builtins import object
import os
import logging
import shutil
import uuid
import yaml

import outline
import outline.exception
import outline.layer


__all__ = ["is_session_path",
           "Session"]

logger = logging.getLogger("outline.session")


def is_session_path(folder):
    """
    Return true if the specified folder contains an outline session.

    :type  folder: str
    :param folder: The folder to check.

    :rtype: boolean
    :return: true if the given folder contains an outline session.
    """
    if not folder:
        return False
    if not os.path.isdir(folder):
        folder = os.path.abspath(os.path.dirname(folder))
    if not os.path.exists(os.path.join(folder, 'session')):
        logger.info("script is not part of an existing session.")
        return False
    return True


class Session(object):
    """
    The session provides global storage space for an outline.  This
    global storage space is usually located in cue/cue_archive but
    may be in a different location based on L{outline.config}.

    Using put_file, get_file you can copy files into this location which
    can be used by all frames. Using put_data, get_data you can
    serialize and deserialize data into this session than can be used
    by all frames.
    """

    def __init__(self, ol):
        object.__init__(self)

        # The outline object that the session is for.
        self.__outline = ol

        # The unique session name is either set by creating a new
        # session or loading an existing one.
        self.__name = None

        # The path of a loaded session.
        self.__path = None

        if is_session_path(self.__outline.get_path()):
            self.__load_session()
        else:
            self.__create_session()

    def __create_session(self):
        """Create and set a new session path."""

        logger.info("Creating new session path.")
        try:
            job_name = "%s-%s-%s_%s" % (self.__outline.get_show(),
                                        self.__outline.get_shot(),
                                        self.__outline.get_user(),
                                        self.__outline.get_name())

            # This is unique session name.  Its a combination
            # of the job name and a random uuid.
            self.__name = "%s/%s" % (job_name, uuid.uuid1())

            # The base dir is where we copy the outline and
            # store session data.
            base_path = outline.config.get("outline", "session_dir")
            base_path = base_path.format(
                HOME=os.path.expanduser("~"),
                SHOW=self.__outline.get_show(),
                SHOT=self.__outline.get_shot())
            base_path = os.path.join(base_path, self.__name)

            # If the base dir doesn't exist, create it.  Be sure
            # to make a directory to store the layer data.
            if not os.path.exists(base_path):
                logger.info("creating session path: %s", base_path)
                old_mask = os.umask(0)
                try:
                    os.makedirs(base_path, 0o777)
                    os.mkdir("%s/layers" % base_path, 0o777)
                finally:
                    os.umask(old_mask)

            # finally, set the session path so any calls to get_path
            # will return the proper value.
            self.__path = base_path

        except OSError as exp:
            msg = "Failed to create session path: %s, reason: %s"
            raise outline.exception.SessionException(msg % (self.get_path(), exp))

    def __load_session(self):
        """Loads an existing session based on the current path."""

        session = "%s/session" % (os.path.dirname(self.__outline.get_path()))
        if not os.path.exists(session):
            msg = "Invalid session %s, session file does not exist."
            raise outline.exception.SessionException(msg % session)

        logger.info("loading session: %s", session)
        with open(session, encoding='utf-8') as file_object:
            try:
                data = yaml.load(file_object, Loader=yaml.Loader)
            except Exception as exp:
                msg = "failed to load session from %s, %s"
                raise outline.exception.SessionException(msg % (session, exp))
        self.__name = data
        self.__path = os.path.dirname(self.__outline.get_path())
        logger.info("session loaded: %s", self.__name)

    def get_name(self):
        """
        Return the name of the session.  The session name format is:
        I{non-unique id/unique uuid}

        :rtype: str
        :return: The name of the session.
        """
        return str(self.__name)

    def save(self):
        """Save the current session file."""

        with open(f"{self.get_path()}/session", "w", encoding="utf-8") as fp:
            fp.write(self.__name)

    @staticmethod
    def __layer_name(layer):
        """
        Helper function to conform an layer object or name
        into a string.

        :rtype: str
        :return: the name of the given layer.
        """
        if isinstance(layer, outline.layer.Layer):
            return layer.get_name()
        return str(layer)

    def sym_file(self, src, layer=None, rename=None):
        """
        Symlink a file into the session and return the path
        of the symlink. If the destination file already
        exists it will be deleted first.

        :type  src: str
        :param src: The source path for the file to symlink.

        :type  layer: L{Layer} or str
        :param layer: Layer to copy file into. [Optional]

        :type  rename: str
        :param rename: A new name for the file. [Optional]

        :rtype: str
        :return: The full path to the new file in the session.
        """
        dst = [self.get_path(layer)]
        if rename:
            dst.append(rename)
        else:
            dst.append(os.path.basename(src))

        dst_path = "/".join(dst)
        logger.info("creating session link %s", dst_path)
        try:
            os.unlink(dst_path)
        except (OSError, FileNotFoundError):
            pass
        os.symlink(os.path.abspath(src), dst_path)

        return dst_path

    def put_file(self, src, layer=None, rename=None):
        """
        Copy a file into the session and return the new path.  This
        is used to create local versions of input files for the
        job to use while its running.

        For example, if you had a scene file of some kind, you could:

           - I{session.put_file("comp/chambers/comp_v1.nuke",rename="scene")}

        Using, get_file, you could obtain the new full path to this file.

           - I{path = session.get_file("scene")}

        :type  src: str
        :param src: The source path for the file to copy.

        :type  layer: L{Layer} or str
        :param layer: Layer to copy file into. [Optional]

        :type  rename: str
        :param rename: A new name for the file. [Optional]

        :rtype: str
        :return: The full path to the new file in the session.
        """

        dst = [self.get_path(layer)]
        if rename:
            dst.append(rename)
        else:
            dst.append(os.path.basename(src))

        dst_path = "/".join(dst)

        logger.info("creating session file %s", dst_path)

        shutil.copy(os.path.abspath(src), dst_path)
        return dst_path

    def get_file(self, name, layer=None, check=True, new=False):
        """
        Retrieve the full path to the given file name previously stored
        with :meth:`put_file`.

        :type  name: str
        :param name: The unique identifier for the file.

        :type  layer: outline.layer.Layer or str
        :param layer: outline.layer.Layer or name of layer, optional

        :type check: bool
        :param check: If check is set, an exception is thrown if
                      the file does not exist, defaults to `True`

        :type new: bool
        :param new: If new is set and the file your getting already
                    exists, a SessionException is thrown.  This ensures
                    if your getting a new path to open in the session that
                    the file does not already exist. If new is specified,
                    check is automatically set to false, defaults to `False`

        :rtype: str
        :return: The full path to the file stored under the
                 given name.
        """
        # If new is activated then check should obviously be false.
        if new:
            check = False

        path = "%s/%s" % (self.get_path(layer), name)

        if check:
            if not os.path.exists(path):
                raise outline.exception.SessionException("The path %s does not exist." % path)

        if new:
            if os.path.exists(path):
                raise outline.exception.SessionException("The path %s already exists " % path)

        return path

    def put_data(self, name, data, layer=None, force=False):
        """
        Serialize a primitive variable or structure and store
        it into the session under the specified name.

        Call this to pass data from frame to frame.

        :type  name: str
        :param name: A unique name for the data
        :type  data: mixed
        :param data: Any python object that can be pickled.
        :type  layer: outline.layer.Layer or str
        :param layer: The layer to store the data under. Leave this
                      as None if the data is for the whole job.
                      [Optional]
        :type  force: bool
        :param force: Overwrite data with the same name if it exists.
                      [Optional]
        """

        path = "%s/%s" % (self.get_path(layer), name)
        if os.path.exists(path) and not force:
            raise outline.exception.SessionException("There is already data being \
                stored under this name.")

        with open(path, "w", encoding="utf-8") as fp:
            fp.write(yaml.dump(data))

    def get_data(self, name, layer=None):
        """
        Retrieve previously stored session data stored
        under the specified name.

        :type  name: str
        :param name: The name given to the data.
        :type  layer: L{Layer} or str
        :param layer: The layer the data was stored under. [Optional]

        :rtype: mixed
        :return: Previously stored data.
        """

        path = "%s/%s" % (self.get_path(layer), name)
        if not os.path.exists(path):
            raise outline.exception.SessionException("There is not data in the session \
                stored under that name.")

        logger.debug("opening data path for %s : %s", name, path)
        with open(path, encoding='utf-8') as file_object:
            try:
                return yaml.load(file_object, Loader=yaml.Loader)
            except Exception as exp:
                msg = "failed to load yaml data from %s, %s"
                raise outline.exception.SessionException(msg % (path, exp))

    def get_path(self, layer=None):
        """
        Return the session path for the current job.  If a layer is
        specified, will return the session path for the layer.

        The session path can be used for temporary file storage on
        the shot tree. See L{Layer} get_temp_dir() for a a way to obtain
        a temporary directory on the local hard drive.

        Note: get_path() creates the layer session paths on demand.
        So, you must use get_path(layer) to obtain the layer session path
        or it may not exist if you construct the path on your own.

        :type  layer: L{Layer} or str
        :param layer: Specify the layer to get its session path. [Optional]

        :rtype: str
        :return: The path where session data is stored.

        """
        if not self.__name:
            msg = "error, the session does not have a name."
            raise outline.exception.SessionException(msg)

        if not layer:
            return "%s" % self.__path

        layer_name = self.__layer_name(layer)
        path = "%s/layers/%s" % (self.__path,
                                 layer_name)
        if os.path.exists(path):
            return path
        old_mask = os.umask(0)
        try:
            os.mkdir(path, 0o777)
        except OSError:
            # Just eat this.  If it did actually fail
            # the whole process will fail pretty soon.
            pass
        finally:
            os.umask(old_mask)

        return path
