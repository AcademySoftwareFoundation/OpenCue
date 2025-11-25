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


"""Base classes for all outline modules."""

from __future__ import annotations
from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

import os
import sys
import logging
import tempfile
from typing import (
    TypedDict,
    List,
    Optional,
    Callable,
    Dict,
    Any,
    Union,
    Tuple,
    Set,
)

import FileSequence

import outline
import outline.constants
import outline.depend
import outline.event
import outline.exception
import outline.io
import outline.util

if sys.version_info >= (3, 12):
    from typing import override, Unpack
else:
    from typing_extensions import override, Unpack

__all__ = [
    "Layer",
    "Frame",
    "LayerPreProcess",
    "LayerPostProcess",
    "OutlinePostCommand",
]

logger = logging.getLogger("outline.layer")

DEFAULT_FRAME_RANGE = "1000-1000"


class _LayerArgs(TypedDict, total=False):
    """Typed dict to annotate layer argument names and types.

    This list is most likely incomplete. Add more args as needed.
    """

    chunk: int  # Size of frame chunks
    command: List[str]  # Command to execute
    cores: int  # Minimum number of CPU cores required
    env: Dict[str, str]  # Environment variables to set
    limits: List[str]  # List of limit names
    memory: str  # Minimum memory required
    range: str  # Frame range
    # register: Whether to automatically add the layer
    # to the current outline (default: True)
    register: bool
    service: str  # Name of the service used by the layer
    tags: List[str]  # List of tags to set on the layer
    timeout: int  # Timeout in seconds before considering a frame hung
    # timeout_llu: Timeout for long last update in seconds
    # before considering a frame hung
    timeout_llu: int
    type: outline.constants.LayerType  # The layer type (Render, Util, Post)


class Layer:
    """Base class for all outline modules."""

    def __init__(self, name: str, **args: Unpack[_LayerArgs]) -> None:
        super().__init__()

        self.__name = name

        # Contains the args hash.
        self.__args = self.get_default_args(merge=args)

        # Default the layer type to the Render type as
        # defined in the constants module
        self.__type: Optional[outline.constants.LayerType] = None
        self.set_type(args.get("type", outline.constants.LayerType.RENDER))

        # A set of arguments that is required before
        # the Layer can be launched.
        self.__req_args: Set[Tuple[str, Any]] = set()

        # A list to store what this layer depends on.
        self.__depends: List[outline.depend.Depend] = []

        # If this layer is embedded within another layer
        # the parent value will point to that layer.
        self.__parent: Optional[Layer] = None

        # Contains IO objects that are considered input.
        self.__input: Dict[str, Any] = {}

        # Contains IO objects that are considered output.
        self.__output: Dict[str, Any] = {}

        # A dictionary of environment variables to apply before execute.
        self.__env = {}
        self.__env.update(args.get("env", {}))

        # Children are unregistered layers that are executed
        # after the parent layer.
        self.__children: List[Layer] = []

        # The default name of the service.
        self.__service = self.__args.get("service", "shell")

        # The layer limits.
        self.__limits = self.__args.get("limits")

        # The current frame number.
        self.__frame: Optional[int] = None

        # Initialize the outline instance.
        self.__outline: Optional[outline.Outline] = None

        # Register an event handler.
        self.__evh = outline.event.EventHandler(self)

        # Keep an array of all pre-process frames.
        self.__preprocess_layers: List[LayerPreProcess] = []

        logger.debug(
            "module %s loaded from %s",
            self.__class__.__name__,
            os.path.realpath(__file__),
        )

        self._register()
        self._init_plugins()


    @override
    def __str__(self) -> str:
        return self.get_name()

    @override
    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__} "
            f"name='{self.get_name()}' "
            f"type='{self.get_type()}' "
            f"at {hex(id(self))}>"
        )

    def _register(self):
        if outline.current_outline():
            outline.current_outline().add_layer(self)

    def _init_plugins(self):
        """Initialize all plugins for this layer."""
        # Prevent a circular dependency.
        # pylint: disable=import-outside-toplevel
        from outline.plugins import PluginManager

        for plugin in PluginManager.get_plugins():
            try:
                plugin.init(self)
            except AttributeError:
                pass
        return self

    def _after_init(self, ol: outline.Outline) -> None:
        """
        This method should be implemented by a subclass.
        Executed after a layer has been initialized and added to an outline.
        """

    def after_init(self, ol: outline.Outline) -> None:
        """
        Executed after a layer has been initialized and added to an outline.
        Emits an event.AFTER_INIT signal.
        """
        self._after_init(ol)
        self.__evh.emit(outline.event.LayerEvent(outline.event.AFTER_INIT, self))

    def _after_parented(self, parent: Layer) -> None:
        """
        This method should be implemented by a subclass.
        Executed after a layer has been initialized and added as a child to another layer.
        """

    def after_parented(self, parent: Layer) -> None:
        """
        Automatically called when this Layer instance is parented to another layer instance.
        """
        self._after_parented(parent)
        self.__evh.emit(outline.event.LayerEvent(outline.event.AFTER_PARENTED, self))

    def _before_execute(self) -> None:
        """
        This method should be implemented by a subclass.
        Executed before all execute checks are started.
        """

    def before_execute(self) -> None:
        """
        Executed before all execute checks are started.
        """
        self._before_execute()
        self.__evh.emit(outline.event.LayerEvent(outline.event.BEFORE_EXECUTE, self))

    def _after_execute(self) -> None:
        """
        This method should be implemented by a subclass.
        Executed after the execute() method has been run even if the frame failed.
        Used for cleanup operations that should run even after a frame failure.
        """

    def after_execute(self) -> None:
        """
        Executed after the execute() method has been run even if the frame failed.
        Used for cleanup operations that should run even after a frame failure.
        """
        self._after_execute()
        frames = self.get_local_frame_set(self.__frame)
        self.__evh.emit(
            outline.event.LayerEvent(outline.event.AFTER_EXECUTE, self, frames=frames)
        )

    @staticmethod
    def system(cmd: List[str], ignore_error: bool = False, frame: Optional[int] = None):
        """
        Convenience method for calling io.system(). Shell out to the given command
        and wait for it to finish.

        :see: L{io.system}

        :type  cmd: list<str>
        :param cmd: The command to execute.

        :type ignore_error: boolean
        :param ignore_error: If True, ignore any L{OSError} or shell command failures.
        """
        outline.io.system(cmd, ignore_error, frame)

    def get_default_args(self, merge: Optional[Unpack[_LayerArgs]] = None):
        """
        Create and return a default argument hash. Optionally merge
        the specified dictionary into the result.
        """
        # No backend specific defaults should be here; those values
        # would be defined within the relevant backend module or in
        # the outline configuration file.

        defaults: Dict[str, Any] = {
            # By default, all layers are registered. Registered layers show up
            # as discrete layers. Unregistered layers are generally embedded
            # in registered layers.
            "register": True,
            # The default chunk size.
            "chunk": 1,
            # A null frame range indicates the event
            # will default to the overall frame range
            # defined in the parent outline.
            "range": None,
        }

        # Now apply any settings found in the configuration file.
        # These settings override the procedural defaults set in
        # the layer constructor using default_arg method.
        if outline.config.has_section(self.__class__.__name__):
            for key, value in outline.config.items(self.__class__.__name__):
                defaults[key] = value

        # Now apply user-supplied arguments. These arguments override
        # both the defaults and the class configuration file.
        if merge:
            defaults.update(merge)

        return defaults

    def get_parent(self) -> Optional[Layer]:
        """Return the parent Layer."""
        return self.__parent

    def set_parent(self, layer: Layer) -> None:
        """Set the parent layer."""

        if not isinstance(layer, Layer):
            raise outline.exception.LayerException(
                "Parent instance must derive from Layer."
            )

        self.__parent = layer

    def add_child(self, layer: Layer) -> None:
        """
        Add a child layer to this layer. Child layers are
        executed after the parent layer.
        """
        if not isinstance(layer, Layer):
            raise outline.exception.LayerException(
                "Child instances must derive from Layer."
            )

        layer.set_outline(self.get_outline())
        layer.set_parent(self)

        self.__children.append(layer)
        layer.after_parented(self)

    def add_event_listener(self, event_type: str, callback: Callable) -> None:
        """Add an event listener to the layer's event handler."""
        self.__evh.add_event_listener(event_type, callback)

    def get_event_handler(self) -> outline.event.EventHandler:
        """
        Return the layer's internal EventHandler.
        """
        return self.__evh

    def get_children(self) -> List[Layer]:
        """Return a list of this layer's child layers."""
        return list(self.__children)

    def set_env(self, key: str, value: str) -> None:
        """Set an environment variable to be applied before execute."""
        if key in self.__env:
            logger.warning(
                "Overwriting outline env var: %s, from %s to %s",
                key,
                self.__env[key],
                value,
            )
        self.__env[str(key)] = str(value)

    def get_env(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get the value of the environment variable that will be set before execute."""
        return self.__env.get(key, default)

    def get_envs(self) -> Dict[str, str]:
        """Return all environment variables for this layer."""
        return self.__env

    def get_name(self) -> str:
        """Return the layer name."""
        if self.__parent:
            return f"{self.__parent.get_name()}.{self.__name}"
        return self.__name

    def set_name(self, name: str) -> None:
        """
        Set the layer's name.

        :type name: str
        :param name: A name for the layer.
        """
        if self.__outline and self.__outline.get_mode() > 1:
            msg = "Layer names may only be changed in outline init mode."
            raise outline.exception.LayerException(msg)
        self.__name = name

    def get_type(self) -> outline.constants.LayerType:
        """
        Return the general scope or purpose of the Layer. Allowed
        types are:

            - Render: a general-purpose rendering layer, has inputs and outputs.
            - Util: a setup/cleanup frame or trivial shell command.
            - Post: a post layer which is kicked off after all other layers have completed.
        """
        return self.__type

    def set_type(self, t: outline.constants.LayerType) -> None:
        """
        Set the general scope/purpose of this layer.
        """
        try:
            typ = outline.constants.LayerType(t)
        except ValueError:
            raise outline.exception.LayerException(
                f"{t} is not a valid layer type: {list(outline.constants.LayerType)}"
            )
        self.__type = typ

    def get_outline(self) -> Optional[outline.Outline]:
        """Return the parent outline object."""
        if self.__parent:
            return self.__parent.get_outline()
        return self.__outline

    def set_outline(self, new_outline: outline.Outline) -> None:
        """Set this layer's parent outline to the given outline object."""
        self.__outline = new_outline

    def setup(self) -> None:
        """Setup is run once before the job is launched to the render farm.
        This method would be used for any pre-launch operations that may be required.
        """
        self.check_required_args()
        self._setup()

        for child in self.__children:
            child.setup()

        # Emit the setup event.
        self.__evh.emit(outline.event.LayerEvent(outline.event.SETUP, self))

    def _setup(self) -> None:
        """This method should be implemented by a subclass."""

    def _execute(self, frames: FileSequence.FrameSet) -> None:
        """This method should be implemented by a subclass."""

    def execute(self, frame: int) -> None:
        """
        Execute the local frame set. This typically happens
        on a cluster node.

        :type    frame: int
        :param   frame: The frame to execute.
        """
        # Set the current frame number
        self.__frame = frame

        # Set any arg overrides from args_override in the session
        self.setup_args_override()

        # Find the local frame set, i.e., the frames that this
        # instance is responsible for.
        frames = self.get_local_frame_set(frame)

        # Set OL_ environment variables.
        self.__setup_frame_environment(frames)

        # Process the python_path option
        self.__set_python_path()

        # Load any outputs found in ol:outputs
        self.load_outputs()

        # Run the pre-execute method to setup any variables that could not
        # be serialized.
        self.before_execute()

        # Attempt to create all output file paths.
        self.__create_output_paths()

        # Double check that all required arguments are set.
        self.check_required_args()

        # Check for the existence of required inputs.
        self.check_input(frames)

        # Set all post set shot environment variables.
        for env_k, env_v in self.__outline.get_env().items():
            if not env_v[1]:
                logger.info(
                    "Setting post-set shot environment var: %s %s", env_k, env_v[0]
                )
                os.environ[env_k] = env_v[0]

        # Set all layer-specific post set shot env variables
        try:
            for env_k, env_v in self.__env.items():
                logger.info(
                    "Setting post-set shot environment var: %s %s", env_k, env_v
                )
                os.environ[str(env_k)] = str(env_v)
        except AttributeError:
            pass

        logger.info("Layer %s executing local frame set %s", self.get_name(), frames)

        # Run the subclass's execute method and all child execute methods
        self._execute(frames)
        for child in self.__children:
            child.execute(frame)

        # Run the subclass's _post_execute method
        self.after_execute()

        # Check the existence of required output
        self.check_output(frames)

    # pylint: disable=broad-except,no-member
    def setup_args_override(self) -> None:
        """
        Load the args_override data from the session and set them as the args.
        Useful for when you don't know some args until after launching.
        They are created using::

            layer.put_data('args_override', {'katana_node': 'blah.blah'})

        """
        try:
            args_override = self.get_data("args_override")
            logger.warning("Loaded args_override from session to replace args:")
            for key, value in args_override.items():
                self.set_arg(key, value)
                # This was necessary because plugins/s3d.py uses get_creator()
                if hasattr(self, "get_creator") and self.get_creator():
                    self.get_creator().set_arg(key, value)
                logger.warning("Replaced arg %s with %s", key, value)
        except outline.exception.SessionException:
            logger.debug("args_override not found in session (this is normal)")
        except Exception as e:
            logger.debug("Not loading args_override from session due to %s", e)

    def set_default_arg(self, key: str, value: Any) -> None:
        """
        Set the value for the given argument if and only if the
        argument has not already been set.
        """
        if key not in self.__args:
            self.__args[key] = value

    def get_arg(self, key: str, default: Optional[Any] = None) -> Any:
        """
        Return the value associated with the specified key.
        If the value does not exist, return default.
        """
        return self.__args.get(key, default)

    def set_arg(self, key: str, value: Any) -> None:
        """Set the value of key."""

        for arg, rtype in self.__req_args:
            if arg == key and rtype:
                if not isinstance(value, rtype):
                    msg = (
                        f"The arg {arg} for the {self.__class__.__name__} "
                        f"module must be a {rtype}"
                    )
                    raise outline.exception.LayerException(msg)
                break
        self.__args[key] = value

    def is_arg_set(self, key: str) -> bool:
        """Return true if the key exists in the arg hash."""
        return key in self.__args

    def get_args(self) -> Dict[str, Any]:
        """Return the arg dictionary."""
        return dict(self.__args)

    def copy_args_from(self, layer: Layer, *names: str) -> None:
        """
        Copy args from the given layer into this layer.
        """
        for arg_name in names:
            self.set_arg(arg_name, layer.get_arg(arg_name))

    def get_path(self) -> str:
        """Return the session path for the layer."""
        return self.__outline.get_session().get_path(layer=self)

    def get_session(self) -> outline.session.Session:
        """Return outline's session variable."""
        return self.__outline.get_session()

    def get_service(self) -> str:
        """
        Return the layer's service name. The service
        is the primary application being run in the
        layer.

        :rtype: str
        :return: Name of service.
        """
        return self.__service

    def set_service(self, service: str) -> None:
        """
        Set the service for this layer. The service
        is the name of the primary application being
        run in the layer.

        :type service: string
        :param service: The name of the primary application.
        """
        self.__service = service

    def get_limits(self) -> Optional[List[str]]:
        """
        Return a list of limits for this layer.
        :rtype: list
        :return: list of limits
        """
        return self.__limits

    def set_limits(self, limits: List[str]) -> None:
        """
        Set the limits for this layer.
        :type  limits: list
        :param limits: list of limit names
        """
        self.__limits = limits

    def put_data(self, key: str, value: Any, force: bool = False) -> None:
        """
        Copy a variable into the layer's session.

        :type   key: string
        :param  key: a unique name for the data.
        :type   value: object
        :param  value: the variable you wish to store.
        """
        self.__outline.get_session().put_data(key, value, self, force=force)

    def get_data(self, key: str) -> Any:
        """
        Retrieve a previously saved variable from the session.

        :type  key: string
        :param key: the name that was used to store the value.
        """
        return self.__outline.get_session().get_data(key, self)

    def sym_file(self, src: str, rename: Optional[str] = None) -> str:
        """
        Symlink the given file into the layer's session path. If
        the optional rename argument is set, the file will be
        renamed during the symlink.

        :type src:  string
        :param src: The path to the source file.

        :type rename: string
        :param rename: Rename the src file during the symlink.

        :rtype: str
        :return: The full path to the new file in the session.
        """
        return self.__outline.get_session().sym_file(
            src,
            layer=self,
            rename=rename,
        )

    def put_file(self, src: str, rename: Optional[str] = None) -> str:
        """
        Copy the given file into the layer's session path. If
        the optional rename argument is set, the file will be
        renamed during the copy.

        :type src:  string
        :param src: The path to the source file.

        :type rename: string
        :param rename: Rename the src file during the copy.

        :rtype: str
        :return: The full path to the new file in the session.
        """
        return self.__outline.get_session().put_file(
            src,
            layer=self,
            rename=rename,
        )

    def get_file(self, name: str, check: bool = True, new: bool = False) -> str:
        """
        Retrieve the session path to the given file. The
        file does not have to exist.

        :type name: str
        :param name: The base name of the file.

        :type check: boolean<True>
        :param check: If check is set, an exception is thrown if
                      the file does not exist.

        :type new: boolean <False>
        :param new: If new is set and the file you're getting already
                    exists, a SessionException is thrown. This ensures
                    that when requesting a new path to open in the session
                    the file does not already exist. If new is specified,
                    check is automatically set to False.

        :rtype: str
        :return: the full path to the file stored under the given name.
        """
        return self.__outline.get_session().get_file(
            name,
            layer=self,
            check=check,
            new=new,
        )

    def require_arg(self, key: str, rtype: Optional[Any] = None) -> None:
        """Require the specified key to be present."""
        self.__req_args.add((key, rtype))

    def set_frame_range(self, frame_range) -> None:
        """Set the layer's frame range."""
        logger.debug(
            "layer %s changing range from %s to %s",
            self.get_name(),
            self.__args["range"],
            frame_range,
        )
        self.__args["range"] = str(frame_range)

    # pylint: disable=inconsistent-return-statements
    def get_frame_range(self):
        """
        Return the layer's frame range. If the layer and its
        parent outline file have incompatible frame ranges,
        return None.

        :rtype:    String
        :return:   The layer's frame range.
        """
        if self.__args["range"]:
            rng = self.__args["range"]
        elif self.__parent:
            rng = self.get_parent().get_frame_range()
        else:
            rng = None

        if self.__outline:
            # If there is a layer range and an outline range, return
            # the intersection. If the intersection cannot be
            # made then a LayerException is thrown.

            # If there is just a layer range, return the layer range.
            # If there is no layer range but an outline range, return the outline range.
            # If there is neither a layer range nor an outline range, return a single frame range.

            if rng and self.__outline.get_frame_range():
                ol_rng = FileSequence.FrameSet(self.__outline.get_frame_range())
                ly_rng = FileSequence.FrameSet(rng)

                intersect = outline.util.intersect_frame_set(
                    ol_rng, ly_rng, normalize=False
                )
                if not intersect:
                    return None

                # If normalizing does not change the order of frames, return normalized
                normalized = FileSequence.FrameSet(str(intersect))
                normalized.normalize()
                if list(intersect) == list(normalized):
                    return str(normalized)

                return str(intersect)
            if rng:
                return rng

            if not rng and self.__outline.get_frame_range():
                return self.__outline.get_frame_range()

            if not rng and not self.__outline.get_frame_range():
                return DEFAULT_FRAME_RANGE
        else:
            # There is no parent outline
            if rng:
                return rng
            return DEFAULT_FRAME_RANGE

    def get_local_frame_set(self, start_frame: int) -> FileSequence.FrameSet:
        """
        Compute the local frame set. The local frame set is the frame
        list that must be handled by the execute() function. The local
        frame set can include more than one frame when chunk_size is greater
        than 1.

        :type    start_frame: int
        :param   start_frame: the starting frame of the frame set.
        """
        chunk = self.get_chunk_size()

        if chunk == 1:
            return outline.util.make_frame_set([int(start_frame)])

        local_frame_set = []
        #
        # Remove the duplicates out of our frame range.
        #
        frame_range = FileSequence.FrameSet(self.get_frame_range())
        frame_set = outline.util.disaggregate_frame_set(frame_range)

        #
        # Now find the index for the current frame and start
        # the frame there. Find all frames this instance
        # is responsible for.
        #
        idx = frame_set.index(int(start_frame))
        for i in range(idx, idx + chunk):
            try:
                if frame_set[i] in local_frame_set:
                    continue
                local_frame_set.append(frame_set[i])
            except IndexError:
                break
        if not local_frame_set:
            msg = f"Frame {start_frame} is outside of the frame range."
            raise outline.exception.LayerException(msg)
        return outline.util.make_frame_set(local_frame_set)

    def set_chunk_size(self, size: int) -> None:
        """
        Set the event's chunk size. The chunk size determines how many frames
        each execute will handle.

        :type    size: int
        :param   size: The size of the chunks.
        """
        self.__args["chunk"] = int(size)

    def get_chunk_size(self) -> int:
        """
        Return the chunk size.

        :rtype: int
        :returns: The event's chunk size.
        """
        return int(self.__args["chunk"])

    def depend_previous(self, on_layer: Layer) -> None:
        """
        Setup a previous-frame dependency on the given layer.

        :type on_layer: L{Layer}
        :param on_layer: The L{Layer} to depend on.
        """
        self.depend_on(on_layer, outline.depend.DependType.PreviousFrame)

    def depend_all(
        self, on_layer: Layer, propigate: bool = False, any_frame: bool = False
    ) -> None:
        """
        Setup a layer-on-layer dependency on the given layer.

        :type on_layer: L{Layer}
        :param on_layer: The L{Layer} to depend on.

        :type propigate: boolean
        :param propigate: Whether or not to propagate the dependency to
                          other layers. Defaults to False.

        :type any_frame: boolean
        :param any_frame: Whether or not to setup an 'any-frame' dependency.
                          Defaults to False.
        """
        self.depend_on(
            self.__resolve_layer_name(on_layer),
            outline.depend.DependType.LayerOnLayer,
            propigate,
            any_frame,
        )

    def depend_on(
        self,
        on_layer: Layer,
        depend_type: str = outline.depend.DependType.FrameByFrame,
        propigate: bool = False,
        any_frame: bool = False,
    ) -> None:
        """
        Setup a frame-by-frame or layer-on-layer dependency on the given layer.

        :type on_layer: L{Layer}
        :param on_layer: The L{Layer} to depend on.

        :type propigate: boolean
        :param propigate: Whether or not to propagate the dependency to
                          other layers. Defaults to False.

        :type any_frame: boolean
        :param any_frame: Whether or not to setup an 'any-frame' dependency.
                          Defaults to False.
        """
        # Check for duplicates.
        for depend in self.__depends:
            if depend.get_depend_on_layer() == on_layer:
                logger.info("Skipping duplicated depend %s on %s", self, on_layer)
                return

        if str(self) == str(on_layer):
            logger.info("Skipping setting up dependency on self %s", self)
            return

        try:
            on_layer = self.__resolve_layer_name(on_layer)
        except outline.exception.LayerException:
            logger.warning("%s layer does not exist, depend failed", on_layer)
            return

        logger.info("adding depend %s on %s", self, on_layer)
        #
        # Handle the 'any frame' behavior.
        #
        if any_frame or depend_type == outline.depend.DependType.LayerOnAny:
            if isinstance(self, LayerPreProcess):
                depend_type = outline.depend.DependType.LayerOnLayer
            else:
                depend_type = outline.depend.DependType.FrameByFrame
                any_frame = False
                for pre in self.get_preprocess_layers():
                    pre.depend_on(
                        on_layer,
                        outline.depend.DependType.LayerOnLayer,
                        any_frame=True,
                    )

        depend = outline.depend.Depend(
            self, on_layer, depend_type, propigate, any_frame
        )
        self.__depends.append(depend)

        # Setup pre-process dependencies
        for my_preprocess in self.get_preprocess_layers():
            for on_preprocess in on_layer.get_preprocess_layers():
                # Depend on the layer's pre-process
                my_preprocess.depend_on(
                    on_preprocess, outline.depend.DependType.LayerOnLayer
                )

        #
        # Handle dependency propagation.
        #
        # Propagation occurs when layer A depends on layer B, and
        # layer C depends on layer D, but layer A also depends on layer
        # C, which means layer D must now also depend on layer B.
        #
        # Currently this creates a depend-all (LayerOnLayer) between
        # the propagated dependencies.
        #
        for depend in on_layer.get_depends():
            if depend.is_propagated():
                for my_depend in self.get_depends():
                    dependant = my_depend.get_depend_on_layer()
                    logger.info(
                        "propagating dependency %s -> %s",
                        dependant,
                        depend.get_depend_on_layer(),
                    )
                    dependant.depend_all(depend.get_depend_on_layer(), propigate=False)

    def undepend(self, depend: outline.depend.Depend) -> None:
        """
        Remove the given dependency. If the dependency does not exist
        no exception is thrown.
        """
        try:
            self.__depends.remove(depend)
        except Exception as e:
            logger.warning("failed to remove dependency %s, %s", depend, e)

    def get_depends(self) -> List[outline.depend.Depend]:
        """Return a list of dependencies this layer depends on."""
        # Do not let callers modify the real list.
        return self.__depends

    def get_dependents(self) -> List[outline.depend.Depend]:
        """Return a list of dependencies that depend on this layer."""
        result = []
        for layer in self.__outline.get_layers():
            for depend in layer.get_depends():
                if depend.get_depend_on_layer() == self:
                    result.append(depend)
        return result

    def check_input(self, frame_set: Optional[FileSequence.FrameSet] = None) -> None:
        """
        Check the existence of all required inputs. Raise a LayerException
        if input is missing.
        """
        for name, inpt in self.__input.items():
            if not inpt.get_attribute("checked"):
                continue
            if not inpt.exists(frame_set):
                msg = f"Check input failed ({name}), the path {inpt.get_path()} does not exist."
                raise outline.exception.LayerException(msg)

    def check_output(self, frame_set: Optional[FileSequence.FrameSet] = None) -> None:
        """
        Check the existence of all required outputs. Raise a LayerException
        if output is missing.
        """
        if self.get_arg("nocheck"):
            return
        for name, output in self.__output.items():
            if not output.get_attribute("checked"):
                continue
            if not output.exists(frame_set):
                msg = (
                    f"Check output failed ({name}), "
                    f"the path {output.get_path()} does not exist."
                )
                raise outline.exception.LayerException(msg)

    def add_input(self, name: str, inpt: Any) -> None:
        """
        Add an input to this layer.
        """
        if not name:
            name = f"input{len(self.__input)}"
        name = str(name)
        if name in self.__input:
            msg = f"An input with the name {name} has already been created."
            raise outline.exception.LayerException(msg)

        if not isinstance(inpt, outline.io.Path):
            inpt = outline.io.Path(inpt)

        self.__input[name] = inpt

    def add_output(self, name: str, output: Any) -> None:
        """
        Add an output to this layer.
        """
        if not name:
            name = "output%d" % len(self.__output)
        name = str(name)
        if name in self.__output:
            msg = f"An output with the name {name} has already been created."
            raise outline.exception.LayerException(msg)

        if not isinstance(output, outline.io.Path):
            output = outline.io.Path(output)

        self.__output[name] = output

    def get_inputs(self) -> Dict[str, outline.io.Path]:
        """
        Return dictionary of registered inputs.

        :rtype:  dict
        :return: dictionary of registered inputs.
        """
        return dict(self.__input)

    def get_outputs(self) -> Dict[str, outline.io.Path]:
        """
        Return dictionary of registered outputs.

        :rtype: dict
        :return: dictionary of registered outputs.
        """
        return dict(self.__output)

    def get_input(self, name: str) -> outline.io.Path:
        """
        Return the named input.

        :rtype:  outline.io.Path
        :return: the associated io.Path object for the given name.
        """
        try:
            return self.__input[name]
        except KeyError:
            msg = f"An input by the name {name} does not exist."
            raise outline.exception.LayerException(msg)

    def get_output(self, name: str) -> outline.io.Path:
        """
        Return the named output.

        :rtype:  outline.io.Path
        :return: the associated io.Path object for the given name.
        """
        try:
            return self.__output[name]
        except KeyError:
            msg = f"An output by the name {name} does not exist."
            raise outline.exception.LayerException(msg)

    def set_output_attribute(self, name: str, value: Any) -> None:
        """
        Set the given attribute on all registered outputs.
        """
        logger.debug("Setting output attribute: %s = %s", name, value)
        for output in self.__output.values():
            output.set_attribute(name, value)

    def set_input_attribute(self, name: str, value: Any) -> None:
        """
        Set the given attribute on all registered inputs.
        """
        logger.debug("Setting input attribute: %s = %s", name, value)
        for output in self.__input.values():
            output.set_attribute(name, value)

    @staticmethod
    def get_temp_dir() -> str:
        """
        Return the path to the current temporary directory.
        """
        return tempfile.gettempdir()

    def check_required_args(self) -> None:
        """
        Check required properties.
        If a required property does not exist, raise a LayerException.
        """
        for key, rtype in self.__req_args:
            if key not in self.__args:
                msg = f"The {self} layer requires the {key} property to be set."
                raise outline.exception.LayerException(msg)
            if rtype:
                if not isinstance(self.__args[key], rtype):
                    msg = f"The {self} layer requires {key} to be of the type {rtype}"
                    raise outline.exception.LayerException(msg)

    def get_preprocess_layers(self) -> List[LayerPreProcess]:
        """
        Return all preprocess layers created by this layer.
        """
        return self.__preprocess_layers

    def add_preprocess_layer(self, preprocess: LayerPreProcess) -> None:
        """
        Add a pre-process layer created by this layer.
        """
        self.__preprocess_layers.append(preprocess)

    def load_outputs(self) -> None:
        """
        Detect the existence of an ol:outputs file and add each
        element of the file into this layer's output hash. The data
        in ol:outputs is usually written from a pre-process.
        """
        if not os.path.exists(os.path.join(self.get_path(), "ol:outputs")):
            return
        for name, output in self.get_data("ol:outputs").items():
            self.add_output(name, output)

    def __set_python_path(self) -> None:
        """
        Prepend an array of paths to the python path before execute.
        This method is for testing python libraries prior to release.
        """
        if self.get_arg("python_path"):
            logger.warning("WARNING: PYTHON PATH HAS BEEN ADJUSTED")
            if not isinstance(self.get_arg("python_path"), list):
                logger.warning("python_path should be a list.")
                return
            sys.path = self.get_arg("python_path") + sys.path

    def __setup_frame_environment(self, frames) -> None:
        """
        Set helpful OL_ environment variables.
        """
        os.environ["OL_BASE_SESSION_PATH"] = self.get_outline().get_path()
        os.environ["OL_LAYER_SESSION_PATH"] = self.get_path()
        os.environ["OL_LAYER_RANGE"] = str(frames)

    def __create_output_paths(self) -> None:
        """
        Create directories for all registered outputs if possible. If
        the directory already exists the operation will be skipped.
        """
        for out in self.get_outputs().values():
            if out.get_attribute("mkdir"):
                out.mkdir()

    def __resolve_layer_name(self, layer: Union[str, Layer]) -> Layer:
        """
        Resolve a layer name to a Layer object.
        """
        if not isinstance(layer, Layer):
            return self.get_outline().get_layer(str(layer))
        return layer


class Frame(Layer):
    """
    A Frame is a Layer that represents a single frame. The frame number
    defaults to the first frame of the job.
    """

    @override
    def get_frame_range(self) -> str:
        """
        Return the frame's number. This overrides the get_frame_range
        implementation in Layer so it always returns a single frame.
        Frames are immune to being removed from the job if they do not
        intersect with the job's frame range.

        :rtype:    String
        :return:   The frame number.
        """
        # An outline's frame range might be None; in that case
        # just return the default frame.
        if self.get_outline().get_frame_range():
            seq = FileSequence.FrameSet(self.get_outline().get_frame_range())
            return str(seq[0])
        return DEFAULT_FRAME_RANGE

    @override
    def set_frame_range(self, frame_range) -> None:
        """
        Calling this method does nothing for a Frame.
        """


class LayerPreProcess(Frame):
    """
    A subclass of Frame which must run before the specified
    parent layer is unlocked. The resulting object is automatically named
    "parent_preprocess". A dependency is automatically set up between
    the preprocess and its parent.
    """

    def __init__(self, creator, **args: Unpack[_LayerArgs]):
        super().__init__(
            f"{creator.get_name()}_{args.get('suffix', 'preprocess')}", **args
        )

        self.__creator = creator
        self.__creator.depend_on(
            self, outline.depend.DependType.LayerOnLayer, propigate=False
        )
        self.__creator.add_preprocess_layer(self)

        self.set_type(outline.constants.LayerType.UTIL)
        self.set_service("preprocess")

    def get_creator(self) -> Layer:
        """Return the parent layer (the creator)."""
        return self.__creator

    @override
    def execute(self, frame: int) -> None:
        """
        Perform pre-process execute methods and call
        the superclass's execute method.
        """
        super(LayerPreProcess, self).execute(frame)
        self.__save_outputs()

    @override
    def get_frame_range(self) -> Optional[str]:
        """
        Return the frame's number. This overrides the get_frame_range
        implementation in Frame so it always returns a single frame. If the
        pre-process's creator layer has no valid range then the pre-process
        range should be None as well.

        :rtype:    String
        :return:   The frame number.
        """
        seq = self.__creator.get_frame_range()
        if not seq:
            return None

        fs = FileSequence.FrameSet(seq)
        return str(fs[0])

    def __save_outputs(self) -> None:
        """
        Save outputs set up by the preprocess to the render
        layer's session. The render layer will automatically call
        load_outputs before execution which will load in all output
        data saved out by this method.
        """
        if not self.get_outputs():
            return

        logger.info("Saving %d outputs to ol:outputs", len(self.get_outputs()))
        self.get_creator().put_data("ol:outputs", self.get_outputs(), force=True)


class LayerPostProcess(Frame):
    """
    A subclass of Frame which always runs after the
    specified parent. The resulting object is automatically named
    "parent_postprocess". A dependency is automatically set up between
    the parent and the post process.
    """

    def __init__(self, creator: Layer, propigate: bool = True, **args: Unpack[_LayerArgs]) -> None:
        super().__init__(f"{creator.get_name()}_postprocess", **args)

        self.__creator = creator
        self.depend_on(creator, outline.depend.DependType.LayerOnLayer, propigate=propigate)

        self.set_type(outline.constants.LayerType.UTIL)

    def get_creator(self) -> Layer:
        """Return the layer that created this post-process."""
        return self.__creator


class OutlinePostCommand(Frame):
    """
    A post command is a special frame that kicks off after the
    outline is complete, even if the outline has failed.
    """

    def __init__(self, name: str, **args: Unpack[_LayerArgs]):
        super().__init__(name, **args)
        self.set_type(outline.constants.LayerType.POST)
        self.set_service("postprocess")
