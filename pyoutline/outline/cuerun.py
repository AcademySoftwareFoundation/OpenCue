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
Outline launching and frame execution utilities.
"""

from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

from builtins import object
import logging
import os
import re
# pylint: disable=deprecated-module
from optparse import OptionParser, OptionGroup

import FileSequence

from .config import config
from . import constants
from .layer import Frame
from .loader import load_outline
from . import util


logger = logging.getLogger("outline.cuerun")

__all__ = ["OutlineLauncher",
           "CuerunOptionParser",
           "launch"]


def execute_frame(script, layer, frame):
    """
    Execute the specified frame.
    """
    ol = load_outline(script)
    ol.get_layer(layer).execute(int(frame))


def import_backend_module(name):
    """
    Imports the specified backend queuing system module,
    """
    logger.info("importing [%s] backend module.", name)
    return __import__("outline.backend.%s" % name,
                      globals(), locals(), [name])


def get_launch_facility():
    """
    Return the name of the default launch facility.
    """
    fac = os.environ.get("RENDER_TO", None)
    if not fac:
        fac = os.environ.get("FACILITY",
                             config.get("outline",
                                        "facility"))
    return fac


def launch(ol, use_pycuerun=True, **args):
    """
    A simple convenience method for launching an outline script with
    the most common options.  If you need additional options,
    use the OutlineLauncher class.

    Arguments:

      - B{range}: The frame range in string format. (1-10)
      - B{pause}: Whether or not to launch the job paused.
      - B{wait}: Wait on the job to complete.
      - B{test}: Wait on the job to complete but thrown an exception if
        any frames fail.
      - B{backend}: Sets the queing system backend.  See L{config} for the
        default queueing system.

    :type ol: Outline
    :param ol: The outline file to launch.
    :type use_pycuerun: bool
    :param use_pycuerun: True will wrap the command using pycuerun

    :type args: keyword arguments
    :param args: A dictionary of keyword arguments that control launch
                 parameters.
    """
    launcher = OutlineLauncher(ol, **args)
    return launcher.launch(use_pycuerun)


class OutlineLauncher(object):
    """
    The OutlineLauncher class encapsulates all of the possible
    settings that can be used to launch an outline as well
    as serialize() and launch() methods which call into the
    supplied backend module

    To launch an outline::

        launcher = OutlineLauncher(ol)
        launcher.set_flag("pause", True)
        launcher.set_flag("range", "1-10")
        launcher.launch()

    """
    def __init__(self, outline, **args):
        self.__outline = outline
        self.__flags = {"pause": False,
                        "priority": 1,
                        "wait": False,
                        "test": False,
                        "server": False,
                        "shot": self.__outline.get_shot(),
                        "show": self.__outline.get_show(),
                        "user": self.__outline.get_user(),
                        "dev": False,
                        "devuser": None,
                        "autoeat": False,
                        "range": None,
                        "basename": None,
                        "range_default": False,
                        "nomail": False,
                        "os": False,
                        "env": [],
                        "maxretries": config.get("outline", "maxretries"),
                        "backend": config.get("outline", "backend")}
        self.__flags.update(args)
        self.__backend = None
        facility = self.__outline.get_facility() if self.__outline.get_facility() \
            else get_launch_facility()
        self.set_flag("facility", facility)

    def set_flag(self, key, value):
        """
        Set the value of a launch flag.
        """
        self.__flags[key] = value

    def get_flag(self, key, default=None):
        """
        Get the value of a launch flag.
        """
        return self.__flags.get(key, default)

    def get(self, key):
        """
        Get the value of a launch flag.
        """
        return self.__flags[key]

    def get_outline(self):
        """
        Return the outline file to be launched.
        """
        return self.__outline

    def setup(self):
        """
        Setup the outline for launch."""
        if self.get("range"):
            #
            # If every layer in the job has a layer arg then
            # its determined that the range is "baked" into
            # to job.  If the range has defaulted to the
            # shot range (range_default = True), then the
            # normal intersection rules do not apply.
            #
            if self.get("range_default"):
                fully_baked = True
                for layer in self.__outline.get_layers():
                    # Frames don't have a range by default.
                    if isinstance(layer, Frame):
                        continue
                    if not layer.get_arg("range"):
                        fully_baked = False
                        break
                if not fully_baked:
                    self.__outline.set_frame_range(self.get("range"))
            else:
                self.__outline.set_frame_range(self.get("range"))

        if self.get_flag("shot"):
            os.environ["SHOT"] = self.get_flag("shot")
        if self.get_flag("env"):
            for kvp in self.get_flag("env"):
                k, v = kvp.split("=")
                self.__outline.set_env(k, v)

        # Remove the date that is appended to certain outline
        # file names.
        new_name = re.sub(r"_[\d]{2,4}_[\d]{2}_[\d]{2}_[\d]{2}_[\d]{2}",
                          "", self.__outline.get_name())
        self.__outline.set_name(new_name)
        if self.get_flag("basename"):
            self.__outline.set_name(self.get_flag("basename"))

        self.__outline.setup()

    def launch(self, use_pycuerun=True):
        """
        Launch the outline.  If the outline is not setup to launch
        it will be setup automatically.
        """
        if self.__outline.get_mode() < constants.OUTLINE_MODE_SETUP:
            self.setup()
        return self.__get_backend_module().launch(self, use_pycuerun=use_pycuerun)

    def serialize(self, use_pycuerun=True):
        """
        Serialize and return the outline.  If the outline is not
        setup to launch it will be setup automatically.
        """
        if self.__outline.get_mode() < constants.OUTLINE_MODE_SETUP:
            self.setup()
        if use_pycuerun:
            return self.__get_backend_module().serialize(self)
        return self.__get_backend_module().serialize_simple(self)

    def __get_backend_module(self):
        if self.__backend is None:
            self.__backend = import_backend_module(self.get("backend"))
        return self.__backend

class CuerunOptionParser(OptionParser):
    """
    A subclass of Python's standard OptionParser, this class provides
    a way to version the standard pycuerun arguments.  If a new argument
    is added that is only relevant to version 1.1, then it should only
    show up in version 1.1.
    """

    def __init__(self, **args):
        OptionParser.format_epilog = lambda self, formatter: self.epilog
        OptionParser.__init__(self, **args)
        self.__setup_standard_options()
        # Automatically initialized if any plugin addds an option
        # to the OptionParser.
        self.__plugin_grp = None

    def __setup_standard_options(self):
        """
        Sets up the option parser with all the standard options
        that are common for every cuerun based tool.
        """
        grp_std = OptionGroup(self, "Standard Options")
        self.add_option_group(grp_std)

        grp_std.add_option("-b", "--backend", action="store", dest="backend",
                           default=config.get("outline", "backend"))
        grp_std.add_option("-s", "--server", action="store", dest="server")
        grp_std.add_option("-F", "--facility", action="store", dest="facility",
                           default=get_launch_facility(),
                           help="Set the job facility.")
        grp_std.add_option("-V", "--verbose", action="store_true",
                           dest="verbose", default=False)
        grp_std.add_option("-D", "--debug", action="store_true", dest="debug",
                           default=False)

        grp_dev = OptionGroup(self, "Devlopment Options")
        self.add_option_group(grp_dev)

        grp_dev.add_option("-v", "--version", action="store", dest="version",
                           default=os.getenv("OL_VERSION", "latest"))
        grp_dev.add_option("-r", "--repos", action="store", dest="repos")
        grp_dev.add_option("--dev", action="store_true", dest="dev",
                           help="Add current user's dev areas to python path.")
        grp_dev.add_option("--dev-user", action="store", dest="devuser",
                           help="Add given user's dev areas to python path.")
        grp_dev.add_option("--env", action="append", dest="env",
                           help="Add environment key/value pairs with --env k=v")

        grp_job = OptionGroup(self, "Job Options")
        self.add_option_group(grp_job)

        grp_job.add_option("-p", "--pause", action="store_true", dest="pause",
                           default=False,
                           help="Launch outline script in paused state.")
        grp_job.add_option("-w", "--wait", action="store_true", dest="wait",
                           default=False,
                           help="Block until the launched job is completed.")
        grp_job.add_option("-t", "--test", action="store_true", dest="test",
                           default=False,
                           help="Block until the job is completed or failed.")
        grp_job.add_option("-f", "--range", action="store", dest="range",
                           help="Specify the frame range. Defaults to $FR env variable.")
        grp_job.add_option("--shot", action="store", dest="shot",
                           metavar="SHOT", default=util.get_shot(),
                           help="Switch job to the specified shot.")
        grp_job.add_option("--no-mail", action="store_true", dest="nomail",
                           help="Disable email notifications.")
        grp_job.add_option("--max-retries", action="store", dest="maxretries",
                           help="Set the max number of retries per frame.",
                           default=config.get("outline", "maxretries"))
        grp_job.add_option("-o", "--os", action="store", dest="os",
                           default=os.getenv("OL_OS", ""),
                           help="Set the target operating system for the job.")
        grp_job.add_option("--base-name", action="store", dest="basename",
                           help="Set the base name for the job.")
        grp_job.add_option("--autoeat", action="store_true", dest="autoeat",
                           help="Automatically eat dead frames with no retry.")

    def handle_standard_options(self, options, args):
        """
        Handle standard options common to all cuerun based scripts.
        """
        logger.debug("Options: %s", options)
        logger.debug("Args: %s", args)

        self.setup_frame_range(options, options.range)

    @staticmethod
    def setup_frame_range(options, frange=None):
        """
        Setup the frame range for the given job.
        """
        range_default = False
        if not frange:
            if os.environ.get("FR"):
                # pylint: disable=no-member
                if FileSequence.FrameSet.isSequence(os.environ.get("FR")):
                    frange = os.environ.get("FR")
                    range_default = True

        options.range = frange
        options.range_default = range_default

    def add_plugin_option(self, *args, **kwargs):
        """
        Add an entry to the Plugin group of the option parser.
        """
        if not self.__plugin_grp:
            self.__plugin_grp = OptionGroup(self, "Plugins")
            self.add_option_group(self.__plugin_grp)
        self.__plugin_grp.add_option(*args, **kwargs)

    @staticmethod
    def options_to_args(options):
        """
        Convert an OptionParser namespace into a dictionary.
        """
        return {
                "backend": options.backend,
                "basename": options.basename,
                "server": options.server,
                "pause": options.pause,
                "priority": options.priority,
                "wait": options.wait,
                "test": options.test,
                "range": options.range,
                "range_default": options.range_default,
                "shot": options.shot,
                "dev": options.dev,
                "devuser": options.devuser,
                "facility": options.facility,
                "nomail": options.nomail,
                "maxretries" : options.maxretries,
                "os": options.os,
                "env": options.env,
                "autoeat": options.autoeat,
                }
