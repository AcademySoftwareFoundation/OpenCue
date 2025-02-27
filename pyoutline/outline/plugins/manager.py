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
Module for setting up the PyOutline plugin system.
"""

from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

from builtins import object
import logging
import sys

from outline.config import config


logger = logging.getLogger("outline.plugins")


class PluginManager(object):
    """
    Class responsible for instantiating the plugin system and loading desired plugins.
    """

    registered_plugins = []

    @classmethod
    def init_cuerun_plugins(cls, cuerun):
        """Initialize all registered plugins."""
        for plugin in cls.registered_plugins:
            try:
                plugin.init_cuerun_plugin(cuerun)
            except AttributeError:
                pass

    @classmethod
    def load_plugin(cls, module_name):
        """Load a single plugin and register it with the plugin manager."""
        logger.debug("importing [%s] outline plugin.", module_name)
        try:
            module = __import__(module_name,
                                globals(),
                                locals(),
                                [module_name])
            try:
                module.loaded()
            except AttributeError:
                pass
            cls.registered_plugins.append(module)

        except ImportError as e:
            sys.stderr.write("Warning: plugin load failed: %s\n" % e)

    @classmethod
    def init_plugin(cls, module_name, layer):
        """Initialize a plugin on the given layer."""
        try:
            logger.debug("importing [%s] outline plugin.", module_name)
            plugin = __import__(module_name, globals(), locals(), [module_name])
            try:
                plugin.init(layer)
            except AttributeError:
                pass
        except ImportError as e:
            sys.stderr.write("Warning: plugin load failed: %s\n" % e)

    @classmethod
    def load_all_plugins(cls):
        """Load and register all plugins listed in the config file."""
        def section_priority(section_needing_key):
            priority_option = "priority"
            if config.has_option(section_needing_key, priority_option):
                return config.getint(section_needing_key, priority_option)
            return 0

        sections = sorted(config.sections(), key=section_priority)

        for section in sections:
            if section.startswith("plugin:"):
                if config.getint(section, "enable"):
                    logger.debug("Loading plugin '%s'", section)
                    cls.load_plugin(config.get(section, "module"))

    @classmethod
    def get_plugins(cls):
        """Gets a list of all registered plugins."""
        return cls.registered_plugins
