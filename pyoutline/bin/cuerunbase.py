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


from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

from builtins import object
import logging
import os
import signal
import sys
import traceback

from outline import versions


logging.basicConfig()
logger = logging.getLogger("cuerun")

LOGGING_FORMAT = "[%(asctime)s %(levelname)s %(module)s]:   %(message)s"


def enable_debug_logging():
    """Enable debug logging."""
    logging.basicConfig(level=logging.DEBUG,
                        format=LOGGING_FORMAT)


def enable_verbose_logging():
    """Enable verbose logging."""
    logging.basicConfig(level=logging.WARN,
                        format=LOGGING_FORMAT)


def signal_handler(signum, frame):
    """
    Catch unexpected signals and dump as much info as possible.
    """
    print('caught signal', signum)
    print(frame.f_back)
    print(frame.f_lasti)
    print(frame.f_globals)
    print(frame.f_locals)
    print(frame.f_restricted)
    traceback.print_exc(file=sys.stderr)


def handle_core_arguments():
    """
    Handles the core curun arguments and setup the outline
    environment.  The core arguments are:
    -V,--verbose = turn on verbose logging
    -D,--debug = turn on debug logging
    --version = specify an alternate outline version
    --repos = specify an alternate outline repository

    All of these options need to be handled to setup the right
    environment to imported the versioned cuerun/outline code.

    """
    repos = None
    version = os.environ.get("OL_VERSION", "latest")

    # We can't use an option parser here because we're
    # only checking for a certain args.  Option parsers
    # will bomb out because of unknown options which are
    # handled by the versioned cuerun module.
    for pos, arg in enumerate(sys.argv):
        if arg in ("-V", "--verbose"):
            enable_verbose_logging()
        elif arg in("-D", "--debug"):
            enable_debug_logging()
        elif arg in ("-v", "--version"):
            version = sys.argv[pos+1]
        elif arg in ("-r", "--repos"):
            repos = sys.argv[pos+1]

    setup_outline_environment(version, repos)


def setup_outline_environment(version="latest", repos=None):
    """
    Sets up the environment to execute a specific version
    of outline,
    """
    override = ""
    if repos:
        override = "[OVERRIDE] "
        versions.set_repos(repos)
    versions.require("outline", version)

    logger.info("%sPyOutline repository: %s" %
                (override, versions.get_repos()))
    logger.info("PyOutline version: %s" % version)


class AbstractCuerun(object):
    """
    AbstractCuerun is a starting point for cuerun based tools which
    provides a OptionParser that handles the default set of arguments
    that need to be handled by all cuerun based tools.
    """

    usage = "%s [options]" % __file__
    descr = "A cuerun script."
    epilog = ""

    def __init__(self):
        handle_core_arguments()
        self.__parser = None
        self.__options = {}
        self.__args = []

        self.__setup_parser()
        self.add_my_options()

        from outline import event, PluginManager
        PluginManager.init_cuerun_plugins(self)

        # Register an event handler.
        self.__evh = event.EventHandler(self)

        # Setup a sigbus signal handler.
        try:
            signal.signal(signal.SIGBUS, signal_handler)
        except ValueError:
            # Not every system implements SIGBUS.
            pass

    def add_my_options(self):
        """Implemented by subclass."""
        pass

    def handle_my_options(self, parser, options, args):
        """Implemented by subclass."""
        pass

    def __setup_parser(self):
        """
        Sets up a CuerunOptionParser which handles all the core
        options for cuerun based tools.
        """
        from outline.cuerun import CuerunOptionParser
        self.__parser = CuerunOptionParser(usage=self.__class__.usage,
                                           description=self.__class__.descr,
                                           epilog=self.__class__.epilog)

    def get_parser(self):
        """
        Return the intenral CuerunOptionParser.
        """
        return self.__parser

    def go(self):
        """
        Parse the command line arguments to handle the base
        arguments, then call handle_my_args to process the users
        custom arguments.
        """
        self.__options, self.__args = self.__parser.parse_args()
        self.__parser.handle_standard_options(self.__options, self.__args)
        self.handle_my_options(self.__parser, self.__options, self.__args)

    def options_to_dict(self, options):
        """
        Converts an option array to a dictionary keyed on option name.
        """
        return self.__parser.options_to_args(options)

    def add_event_listener(self, event_type, callback):
        """
        Add an event listener for the given event type.
        """
        self.__evh.add_event_listener(event_type, callback)

    def launch_outline(self, outline, **override):
        """
        Launches the specified outline script with the options parsed
        from the command line.
        """
        from outline import cuerun, config, event

        if self.__options.debug:

            bin_dir = os.path.dirname(os.path.abspath(__file__))
            logger.debug("Overriding cuerun bin directory to %s" % bin_dir)

            # Overide the location of the bin dir to the one where
            # this script is located if we're in debug mode.
            config.set("outline", "bin_dir", bin_dir)

        self.__evh.emit(event.LaunchEvent(event.BEFORE_LAUNCH, self, outline=outline))
        try:
            args = self.options_to_dict(self.__options)
            args.update(override)
            result = cuerun.launch(outline, **args)
            self.__evh.emit(event.LaunchEvent(event.AFTER_LAUNCH, self, job=result, outline=outline))
            return result
        except Exception as e:
            sys.stderr.write("outline failure, %s" % e)
            traceback.print_exc(file=sys.stderr)
            sys.exit(1)
