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


import sys
import logging

from outline.config import config

logger = logging.getLogger("outline.plugins")

class PluginManager(object):

    registered_plugins = []

    @classmethod
    def init_cuerun_plugins(cls, cuerun):
        for plugin in cls.registered_plugins:
            try:
                plugin.init_cuerun_plugin(cuerun)
            except AttributeError, e:
                pass

    @classmethod
    def load_plugin(cls, module_name):
        logger.debug("importing [%s] outline plugin." % module_name)
        try:
            module = __import__(module_name,
                                globals(),
                                locals(),
                                [module_name])
            try:
                module.loaded()
            except  AttributeError, e:
                pass
            cls.registered_plugins.append(module)

        except ImportError, e:
            sys.stderr.write("Warning: plugin load failed: %s\n" % e)

    @classmethod
    def init_plugin(cls, module_name, layer):
        """
        Initialize a plugin on the given layer.
        """
        try:
            logger.debug("importing [%s] outline plugin." % module_name)
            plugin = __import__(module_name, globals(), locals(), [module_name])
            try:
                plugin.init(layer)
            except AttributeError, e:
                pass
        except ImportError, e:
            sys.stderr.write("Warning: plugin load failed: %s\n" % e)

    @classmethod
    def load_all_plugins(cls):        
        def sort_by_priority(a, b):
            priority_option = "priority"
            a_priority = 0
            b_priority = 0
            if config.has_option(a, priority_option):
                a_priority = config.getint(a, priority_option)
            if config.has_option(b, priority_option):
                b_priority = config.getint(b, priority_option)
            return cmp(b_priority, a_priority)
        
        sections = sorted(config.sections(), cmp=sort_by_priority)
        
        for section in sections:
            if section.startswith("plugin:"):
                if config.getint(section, "enable"):
                    logger.debug("Loading plugin '%s'" % section)
                    cls.load_plugin(config.get(section, "module"))

    @classmethod
    def get_plugins(cls):
        return cls.registered_plugins

