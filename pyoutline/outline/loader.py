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


"""Load and parse outline scripts."""


from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

from builtins import str
from builtins import object
import os
import logging
import json
import time
import uuid
import yaml

import FileSequence

import outline.constants
import outline.depend
import outline.exception
# pylint: disable=cyclic-import
import outline.session
import outline.util


logger = logging.getLogger("outline.loader")

__all__ = ["Outline",
           "load_outline",
           "load_json",
           "parse_outline_script",
           "current_outline"]


def load_outline(path):
    """
    Load an outline script. The path can be either an
    outline script or serialized outline script.

    :type  path: str
    :param path: The path to the outline file. Serialized
                 outline files must be named with the .yaml
                 extension. Anything else is considered a python
                 outline script.

    :rtype: Outline
    :return: The resulting Outline object.
    """
    logger.info("loading outline: %s", path)

    # The wan cores may not see this file right away
    # The avere cache will hold a negative cache for 30 seconds, extending every time it is checked
    # The local cache will cache for 30 seconds as well
    if path and not os.path.exists(path):
        logger.info(
            'Outline file does not exist, sleeping 35 seconds before checking again due to '
            'possible file cache latency.')
        time.sleep(35)

    ext = os.path.splitext(path)
    if ext[1] == ".yaml" or path.find("cue_archive") != -1:
        with open(path, encoding='utf-8') as file_object:
            ol = yaml.load(file_object, Loader=yaml.FullLoader)
        Outline.current = ol
        if not isinstance(ol, Outline):
            raise outline.exception.OutlineException("The file %s did not produce "
                                   "an Outline object." % path)
    else:
        # If the file is not .yaml, assume its a python script
        ol = Outline(path=path, current=True)

    # If the script is inside of a session
    if outline.session.is_session_path(path):
        ol.load_session()

    return ol


def load_json(json_str):
    """
    Parse a json representation of an outline file.

    :type  json_str: str
    :param json_str: A json string.

    :rtype: L{Outline}
    :return: The resulting outline object.
    """

    def decode_layer(layer):
        """
        Converts keys to strings to ensure compatibility with Python 3
        """
        result = {}
        for k, v in layer.items():
            result[str(k)] = v
        del result["module"]
        del result["name"]
        return result

    data = json.loads(json_str)
    ol = Outline(current=True)

    if "name" in data:
        ol.set_name(data["name"])
    if "facility" in data:
        ol.set_facility(data["facility"])
    if "maxcores" in data:
        ol.set_maxcores(data["maxcores"])
    if "maxgpus" in data:
        ol.set_maxgpus(data["maxgpus"])
    if "range" in data:
        ol.set_frame_range(data["range"])

    for layer in data["layers"]:
        s_class = None
        try:
            # Get the fully qualified module name, foo.bar.blah
            s_module = ".".join(layer["module"].split(".")[0:-1])
            # Get the class to instantiated.
            s_class = layer["module"].split(".")[-1]

            # Import the module and instantiate the class.
            module = __import__(s_module, globals(), locals(), [s_class])
            cls = getattr(module, s_class)
            cls(layer["name"], **decode_layer(layer))

        except KeyError:
            error = "Json error, layer missing 'name' or 'module' definition"
            raise outline.exception.OutlineException(error)

        except Exception as e:
            msg = "Failed to load plugin: %s , %s"
            raise outline.exception.OutlineException(msg % (s_class, e))

    return ol


def parse_outline_script(path):
    """
    Parse a native outline script and add any layers to
    the current outline's layer list. The current outline
    is optionally set when an outline oject is created by
    passing current=True to the constructor.

    Once the current outline is set, you can execute as many
    outline scripts as you want and the resulting layers become
    part of the current outline.

    :type  path: str
    :param path: The path to the outline file.
    """
    try:
        logger.info("parsing outline file %s", path)
        with open(path, encoding='utf-8') as fp:
            code = compile(fp.read(), path, 'exec')
            exec(code)  # pylint: disable=exec-used
    except Exception as exp:
        logger.warning("failed to parse as python file, %s", exp)
        raise outline.exception.OutlineException(
            "failed to parse outline file: %s, %s" % (path, exp))


def current_outline():
    """
    Return the current outline. The current outline is where all
    new layers are registered. If the current outline is None and
    a new layer is created, you have to explicitiy register the
    layer with an outline object.

    Example:
    I{outline = Outline()}
    I{outline.add_layer(Shell("shell_cmd",["/bin/ls"]))}

    :rtype: L{Outline}
    :return: The current Outline object.
    """
    return Outline.current


def quick_outline(layer):
    """
    Create an instance of an outline, add the given
    layer, and return the outline.

    :type  layer: L{Layer}
    :param layer: A L{Layer} object.

    :rtype: L{Outline}
    :return: An outline file containing the given layer.
    """
    ol = Outline(name=layer.get_name(), current=True)
    ol.add_layer(layer)
    return ol


class Outline(object):
    """The outline class represents a single outline script."""

    # The current outline is maintained here so layers can
    # obtain it to register themselves when the script is
    # being parsed.
    current = None

    def __init__(self, name=None, frame_range=None, path=None,
                 serialize=True, name_unique=False, current=False,
                 shot=None, show=None, user=None, facility=None,
                 maxcores=None, maxgpus=None):
        """
        :type  name: string
        :param name: A name for the outline instance.  This will become
                     part of the job name.

        :type  path: string
        :param path: An optional path to a native outline script.  If your
                     building an outline procedurally this argument
                     is not required.  If a name is not set, the name of
                     the file becomes the name.

        :type  frame_range: string
        :param frame_range: The frame range. Defaults to a single frame.

        :type  current: boolean
        :param current: If true, all newly created layers are
                        automatically parented to this instance.
                        Default to false.
        :type  shot: string
        :param shot: The shot name for this outline instance. If a shot
                     is not provided, it will be looked up using the
                     util.get_shot function.
        :type  show: string
        :param show: The show name for this outline instance. If a show
                     is not provided, it will be looked up using the
                     util.get_show function.
        :type  user: string
        :param user: The user name for this outline instance. If a user
                     name is not provided, it will be looked up using
                     the util.get_user function.
        :type  facility: string
        :param facility: The launch facility to be used. If not specified
                     the RENDER_TO and FACILITY environment variables
                     will be checked.
        :type  maxcores: int
        :param maxcores: The maximum number of CPU cores for the job.

        :type  maxgpus: int
        :param maxgpus: The maximum number of GPU units for the job.
        """
        object.__init__(self)

        # If current is true, then all layer objects that get
        # created will automatically parent to this outline instance.
        if current:
            Outline.current = self

        #
        # The name of the outline. This is appended to
        # SHOW-SHOT-USER_ to form the basis of the job name.
        #
        self.__name = name

        #
        # The default frame range for an outline.  The frame range
        # must be part of the outline data so chunked frames can
        # figure out their frame sets.
        #
        self.__frame_range = None
        self.set_frame_range(frame_range)

        #
        # The shot name for the outline.
        #
        self.__shot = shot

        #
        # The show name for the outline.
        #
        self.__show = show

        #
        # The user name for the outline.
        #
        self.__user = user

        #
        # A user-controlled hash of key value pairs that are
        # serialized with the outline data.
        #
        self.__args = {}

        #
        # See constants for the description of outline modes
        #
        self.__mode = outline.constants.OUTLINE_MODE_INIT

        #
        # Stores the array of layers for this outline.  To
        # add a new layer, use register_layer.
        #
        self.__layers = []

        #
        # A hash of environment variables that are passed up
        # to opencue and then set before each frame is run.
        # These are set "pre" setshot, so they can be used
        # to modify setshot behavior.
        #
        self.__env = {}

        #
        # The launch facility to use, or None.
        #
        self.__facility = facility

        #
        # The maximum number of CPU cores to use, or None.
        #
        self.__maxcores = maxcores

        #
        # The maximum number of CPU cores to use, or None.
        #
        self.__maxgpus = maxgpus

        #
        # The outline session.  The session is setup during the setup
        # phase.  Every job has a unique session which maps to a
        #
        self.__session = None

        #
        # If true, an outline file is yamlized before being
        # copied into the outline session.  If not, the script
        # is copied as is.  Default is True.
        self.__serialize = serialize

        #
        # The path to a native outline script.  If a path
        # is specified in the constructor, then it must
        # be a path to a native (not serialized) outline
        # script.
        #
        self.__path = None

        if path:
            self.__path = path

            # If the name was not previously set, use the name
            # of the outline file.  This allows the user to override
            # the auto-naming based on the outline file name if needed.
            if not self.__name:
                self.__name = self.__get_name_by_path()

            # Now parse the outline script.
            self.parse_outline_script(path)
        else:
            # If the user does not pass in a name or a path to an
            # outline,  give the outline a default name.
            if not self.__name:
                self.__name = "outline"

        if name_unique:
            self.__name = "%s_%s" % (self.__name, str(uuid.uuid4())[0:7])

    def __get_name_by_path(self):
        """Return the name of the session based on the outline."""
        return os.path.splitext(os.path.basename(self.__path))[0]

    def parse_outline_script(self, path):
        """
        Parse an outline script and add the resulting layers
        to this instance.
        """
        Outline.current = self
        parse_outline_script(path)

    def load_session(self):
        """
        Reloads the session
        """
        if outline.session.is_session_path(self.get_path()):
            self.__session = outline.session.Session(self)
        else:
            msg = "failed to load outline %s, not part of a session."
            raise outline.exception.OutlineException(msg % self.get_path())

    def setup(self):
        """
        Sets up the outline to run frames.

        A new session is created for the outline and setup()
        methods are run for each layer.

           - Creates a new session
           - Checks require arguments on all layers.
           - Runs tge setup() method for all layers.
           - Serializes outline structure into the session.
           - Sets the outline state to READY.

        """
        if self.__mode >= outline.constants.OUTLINE_MODE_SETUP:
            raise outline.exception.OutlineException("This outline is already setup.")

        self.setup_depends()

        self.__mode = outline.constants.OUTLINE_MODE_SETUP
        self.__session = outline.session.Session(self)

        # Run setup() for every layer assuming the frame range
        # can be determined.  If there is no frame range, the layer
        # is not going to be launched to the cue.
        for layer in self.__layers:
            if layer.get_frame_range():
                layer.setup()

        # Remove self from the current outline.
        if Outline.current == self:
            Outline.current = None

        if self.__serialize:
            yaml_file = os.path.join(self.__session.get_path(),
                                     "outline.yaml")

            # Set a new path before serialzing the outline file.
            logger.info("setting new outline path: %s", yaml_file)
            self.set_path(yaml_file)

            # Copy the session over to a local variable and unset
            # self.__session. We do not want the session to be
            # archived with the outline because relaunching the
            # job using the serialized outline will fail.
            session = self.__session
            self.__session = None

            # Now copy outline file in.
            logger.info("serializing outline script to session path.")
            session.put_data(os.path.basename(yaml_file), self)

            # Switch the session back in.
            self.__session = session

        elif not self.__serialize and self.get_path():
            logger.info("copying outline script to session path.")
            self.__session.put_file(self.get_path(), None, "script.outline")
        else:
            raise outline.exception.OutlineException(
                "Failed to serialize outline, Procedural outlines must always use serialization.")

        # Set our new mode and save.
        self.set_mode(outline.constants.OUTLINE_MODE_READY)
        self.__session.save()

    def setup_depends(self):
        """
        Iterate through layers and setup any dependencies passed in
        via the "require" argument.
        """
        logger.info("Setting up dependencies")
        for layer in self.get_layers():
            # Setup dependencies passed in via the layer's require argument.
            if layer.get_arg("require", False):
                if not isinstance(layer.get_arg("require"), (tuple, list, set)):
                    require, dtype = outline.depend.parse_require_str(layer.get_arg("require"))
                    try:
                        layer.depend_on(self.get_layer(require), dtype)
                    except outline.exception.OutlineException:
                        logger.warning("Invalid layer in depend %s, skipping", require)
                        continue
                else:
                    # Process the require argument.
                    for require in layer.get_arg("require"):
                        require, dtype = outline.depend.parse_require_str(require)
                        try:
                            layer.depend_on(self.get_layer(str(require)), dtype)
                        except outline.exception.OutlineException:
                            logger.warning("Invalid layer in depend %s, skipping", require)
                            continue

    def add_layer(self, layer):
        """Adds a new layer."""

        if not layer.get_arg("register"):
            return

        if layer in self.__layers:
            logger.info("The layer %s was already added to this outline.", layer.get_name())
            return

        if self.is_layer(layer.get_name()):
            raise outline.exception.OutlineException(
                "The layer %s already exists" % layer.get_name())

        self.__layers.append(layer)
        layer.set_outline(self)
        layer.after_init(self)

        try:
            if getattr(layer, "get_children"):
                for child in layer.get_children():
                    child.set_outline(self)
                    child.after_init(self)
        except AttributeError:
            pass

        # If we're in setup mode, run setup ASAP
        if self.__mode == outline.constants.OUTLINE_MODE_SETUP:
            layer.setup()

        logger.info("adding layer: %s", layer.get_name())

    def remove_layer(self, layer):
        """Remove an existing layer."""

        if self.__mode >= outline.constants.OUTLINE_MODE_SETUP:
            msg = "Cannot remove layers to an outline not in init mode."
            raise outline.exception.OutlineException(msg)

        if layer in self.__layers:
            self.__layers.remove(layer)

    def get_layer(self, name):
        """Return an later by name."""

        layer_map = {evt.get_name(): evt for evt in self.__layers}
        try:
            return layer_map[name]
        except Exception as e:
            raise outline.exception.OutlineException("invalid layer name: %s, %s" % (name, e))

    def get_layers(self):
        """Return the outline's layers

        Modifying the result of this method will not alter the actual
        layer list.  To add a new layer, use register_layer.
        """
        return list(self.__layers)

    def is_layer(self, name):
        """Return true if a layer exists with the specified name."""
        layer_map = {evt.get_name(): evt for evt in self.__layers}
        return name in layer_map

    def get_path(self):
        """Return the path to the outline file."""
        return self.__path

    def set_path(self, path):
        """Return the path to the outline file."""
        self.__path = path

    def set_name(self, name):
        """Set the name of this outline.

        The name is usually based on the name of the outline
        script but its possible to set it manually.  Do not
        include the show-shot-user prefix when setting the
        name.

        Once the outline is setup to launch, changing
        the name has no effect.
        """
        self.__name = name

    def get_name(self):
        """Return the name of the outline."""
        return self.__name

    def get_full_name(self):
        """
        Return the full name of the Outline instance, which
        includes the show, shot, user, and file name.
        """
        if self.__session:
            return self.get_session().get_name().split("/")[0]
        return "%s-%s-%s_%s" % (self.get_show(),
                                self.get_shot(),
                                self.get_user(),
                                self.get_name())

    def get_shot(self):
        """Return the shot for this outline."""
        if self.__shot is None:
            return outline.util.get_shot()
        return self.__shot

    def set_shot(self, shot):
        """Set the shot name for this outline instance.

        :type shot: string
        :param shot: The name of shot to set.
        """
        self.__shot = shot

    def get_show(self):
        """Return the show for this outline."""
        if self.__show is None:
            return outline.util.get_show()
        return self.__show

    def set_show(self, show):
        """Set the show name for this outline instance.

        :type show: string
        :param show: The name of show to set.
        """
        self.__show = show

    def get_user(self):
        """Return the user for this outline."""
        if self.__user is None:
            return outline.util.get_user()
        return self.__user

    def set_user(self, user):
        """Set the user name for this outline instance.

        :type user: string
        :param user: The name of user to set.
        """
        self.__user = user

    def get_facility(self):
        """Return the launch facility for this outline."""
        return self.__facility

    def set_facility(self, facility):
        """Set the launch facility for this outline instance.

        :type facility: string
        :param facility: The name of the facility to set.
        """
        self.__facility = facility

    def get_maxcores(self):
        """Return the maximum number of CPU cores fot this outline."""
        return self.__maxcores

    def set_maxcores(self, maxcores):
        """Set the maximum number of CPU cores for this outline instance.

        :type maxcores: int
        :param maxcores: The maximum number of CPU cores to set.
        """
        self.__maxcores = maxcores

    def get_maxgpus(self):
        """Return the maximum number of GPU units fot this outline."""
        return self.__maxgpus

    def set_maxgpus(self, maxgpus):
        """Set the maximum number of GPU units for this outline instance.

        :type maxcores: int
        :param maxcores: The maximum number of GPU units to set.
        """
        self.__maxgpus = maxgpus

    def get_mode(self):
        """Return the current mode of this outline object.

        See outline.constants for a list of possible modes.  The mode
        cannot be set from outside of the module.
        """
        return self.__mode

    def set_mode(self, mode):
        """Set the current mode of the outline."""
        if mode < self.__mode:
            raise outline.exception.OutlineException("You cannot go back to previous modes.")
        self.__mode = mode

    def get_session(self):
        """
        Return the session object.  An OutlineException is raised if the
        session has not been setup.

        :rtype: outline.session.Session
        :return: The outline's session object.
        """
        if not self.__session:
            raise outline.exception.SessionException("A session has not been created yet.")
        return self.__session

    def set_frame_range(self, frame_range):
        """Set the outline's frame set.  The frame set must be
        assigned before the outline can go into the setup phase.

        :type   frame_range: str or list or set or tuple or FileSequence.FrameSet
        :param  frame_range: The frame range for this outline.
        """
        if isinstance(frame_range, FileSequence.FrameSet):
            self.__frame_range = str(frame_range)
        elif isinstance(frame_range, (list, set, tuple)):
            self.__frame_range = ",".join([str(frame) for
                                           frame in frame_range])
        else:
            self.__frame_range = frame_range

    def get_frame_range(self):
        """Return the outline's default frame range.

        :rtype: String
        :return: The full frame range for the outline.

        """
        return self.__frame_range

    def set_env(self, key, value, pre=False):
        """
        Set an environment variable that is propagated to
        every frame.

        :type  key:  str
        :param key: Name of environment variable.

        :type value: str
        :param value: Value to associate with the name.

        :type pre: boolean
        :param pre: If this value is set to true, the environment
                    variable is applied pre-setshot.  The default
                    is for the environment variable to be set
                    post set shot.

        """
        if key in self.__env:
            logger.warning(
                "Overwriting outline env var: %s, from %s to %s", key, self.__env[key], value)

        if not isinstance(key, str):
            raise outline.exception.OutlineException(
                "Invalid key type for env var: %s" % type(key))

        if not isinstance(value, str):
            raise outline.exception.OutlineException(
                "Invalid value type for env var: %s" % type(value))

        self.__env[key] = (value, pre)

    def get_env(self, key=None):
        """
        Return the environment hash setup using set_env.

        :rtype: dict
        :return: the dictionary of values that will be propagated into
                 every frame's environment on the cue.
        """
        if key:
            return self.__env[key][0]
        return dict(self.__env)

    def get_args(self):
        """
        Return the full dictionary of user defined outline arguments.

        :rtype: dict
        :return: a dict of arbitrary user defined outline arguments.
        """
        return dict(self.__args)

    def set_arg(self, key, value):
        """
        Associate a value with the given key.  Print a warning
        if the key is already associated with another value.

        :type  key:  string
        :param key: Name for the argument.

        :type value: mixed
        :param value: Value to associate with the given key.
        """
        if key in self.__args:
            logger.warning(
                "Overwriting outline argument: %s, from %s to %s", key, self.__args[key], value)
        self.__args[key] = value

    def get_arg(self, key, default=None):
        """
        Return the value associated with the given key.  Throw an
        OutlineException if the key does not exist.  If a default value
        is provided then that value is returned instead of throwing
        an OutlineException.

        If the default value is None, an OutlineException is thrown.

        :type  key:  string
        :param key: The name of the argument.

        :rtype: mixed
        :return: The value associated with the given key.
        """
        try:
            if default is None:
                return self.__args.get(key)
            return self.__args.get(key, default)
        except KeyError:
            raise outline.exception.OutlineException(
                "No arg mapping exists for the value %s" % key)

    def put_file(self, src, rename=None):
        """
        Copy the given file into the job's session path.  If
        the optional rename argument is set, the file will be
        renamed during the copy.

        :type src:  string
        :param src: The path to the source file.

        :type rename: string
        :param rename: Rename the src file during the copy.

        :rtype: str
        :return: The full path to the new file in the session.
        """
        return self.__session.put_file(src, rename=rename)

    def get_file(self, name, check=True, new=False):
        """
        Retrieve the session path path to the given file.  The
        file does not have to exist.

        :type name: str
        :param name: The base name of the file.

        :type check: boolean<True>
        :param check: If check is set, an exception is thrown if
                      the file does not exist.

        :type new: boolean <False>
        :param new: If new is set and the file your getting already
                    exists, a SessionException is thrown.  This ensures
                    if your getting a new path to open in the session that
                    the file does not already exist. If new is specified,
                    check is automatically set to false.

        :rtype: str
        :return: the full path to the file stored under the given name.
        """
        return self.__session.get_file(name, check=check, new=new)

    def put_data(self, key, value, force=False):
        """
        Copy a variable into the layer's session.

        :type   key: string
        :param  key: a unique name for the data.
        :type   value: object
        :param  value: the variable you wish to store.
        """
        self.get_session().put_data(key, value, force=force)

    def get_data(self, key):
        """
        Retrieve a previously saved variable from the session.

        :type  key: string
        :param key: the name that was used to store the value.
        """
        return self.get_session().get_data(key)
