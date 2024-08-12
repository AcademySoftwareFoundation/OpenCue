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
This module provides the ability to find and run plugins.

Each plugin module can or should contain the following:

PLUGIN_NAME        : The displayed name of the plugin.
PLUGIN_CATEGORY    : The submenu that the plugin should be placed in.
PLUGIN_DESCRIPTION : The description shown next to the plugin name.
PLUGIN_REQUIRES    : (optional) The application name that the plugin requires
                   : to load. ex. "CueCommander"
PLUGIN_PROVIDES    : The name of the class that the plugin provides.

When a plugin is instantiated, a reference to the MainWindow is provided to the
constructor.

When a plugin wishes to remove it's instance, it should signal with:
self.emit(QtCore.SIGNAL("closed(PyQt_PyObject)"), self)

You should not have any circular non-weak refrences to yourself. Use weakref.proxy

You may implement __del__ with a print to see if your object is properly removed

The class the plugin provides can have the following functions:
pluginSaveState() : This should return any settings that the plugin would like
                  : to save for the next time it is loaded as a string.
pluginRestoreState(settings) : This will receive any settings that it previously
                             : returned from pluginSaveSettings()
"""


from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

import json

from builtins import str
from builtins import map
from builtins import object
import os
import sys
import traceback
import pickle

from qtpy import QtCore
from qtpy import QtWidgets

import cuegui.Constants
import cuegui.Logger
import cuegui.Utils


logger = cuegui.Logger.getLogger(__file__)

CLASS = "CLASS"
DESCRIPTION = "DESCRIPTION"
CATEGORY = "CATEGORY"

SETTINGS_KEY = 0
SETTINGS_GET = 1
SETTINGS_SET = 2

try:
    JSON_EXCEPTION_CLASS = json.decoder.JSONDecodeError
except AttributeError:
    JSON_EXCEPTION_CLASS = ValueError


class Plugins(object):
    """Main class responsible for loading and managing plugins."""

    # Keyed to name. each is a dictionary with CLASS, DESCRIPTION and optionally CATEGORY
    __plugins = {}
    _loadedPaths = []

    def __init__(self, mainWindow, name):
        """Plugins class initialization.
        @param mainWindow: Application main window reference
        @type  mainWindow: QMainWindow
        @param name: Name of current window
        @type  name: string"""
        self.__running = []
        self.name = name
        self.mainWindow = mainWindow
        self.app = cuegui.app()

        self.__menu_separator = " \t-> "

        # Load plugin paths from the config file
        __pluginPaths = self.app.settings.value("Plugin_Paths", [])
        for path in cuegui.Constants.DEFAULT_PLUGIN_PATHS + __pluginPaths:
            self.loadPluginPath(str(path))

        # Load plugins explicitly listed in the config file
        self.loadConfigFilePlugins("General")
        self.loadConfigFilePlugins(self.name)

    def loadConfigFilePlugins(self, configGroup):
        """Loads plugins explicitly listed in the config file for the window.
        The path is optional if the module is already in the path. The module is
        optional if you just want to add to the path.

        [General]
        Plugins=/example/path/module, package.module2

        The imported module must have an init function and a QMainWindow will be
        passed to it.
        """
        __plugins = self.app.settings.value("%s/Plugins" % configGroup, [])

        for plugin in __plugins:
            path = os.path.dirname(str(plugin))
            if path:
                logger.info("adding path %s", path)
                sys.path.append(path)

        for plugin in __plugins:
            module = os.path.basename(str(plugin))
            if module:
                logger.info("loading module %s", module)
                s_class = module.split(".")[-1]
                # pylint: disable=broad-except
                try:
                    m = __import__(module, globals(), locals(), [s_class])
                    m.init(self.mainWindow)
                    logger.info("plugin loaded %s", module)
                except Exception as e:
                    logger.warning("Failed to load plugin: %s", s_class)
                    list(map(logger.warning, cuegui.Utils.exceptionOutput(e)))

    def __closePlugin(self, pluginBeingClosed):
        """Event handler for when a plugin is closed.

        When a running plugin is closed, this is called and the running plugin is deleted. If it is
        a dock widget then it is removed from the main window.

        @type  pluginBeingClosed: Object
        @param pluginBeingClosed: the plugin widget being closed"""
        for item in self.__running:
            if item[1] == pluginBeingClosed:
                if isinstance(pluginBeingClosed, QtWidgets.QDockWidget):
                    self.mainWindow.removeDockWidget(pluginBeingClosed)
                self.__running.remove(item)
                return

    def runningList(self):
        """Lists all running plugins.

        @return: [("Class_Name_1", PluginClass1_Instance), ("Class_Name_2", PluginClass2_Instance)]
        @rtype:  list"""
        return self.__running

    def saveState(self):
        """Saves the names of all open plugins.

        Calls .saveSettings (if available) on all plugins."""
        opened = []
        for plugin in self.__running:
            # pylint: disable=broad-except
            try:
                if hasattr(plugin[1], "pluginSaveState"):
                    opened.append("%s::%s" % (plugin[0], json.dumps(plugin[1].pluginSaveState())))
            except Exception as e:
                logger.warning("Error saving plugin state for: %s\n%s", plugin[0], e)
        self.app.settings.setValue("%s/Plugins_Opened" % self.name, opened)

    def restoreState(self):
        """Loads any user defined plugin directories and restores all open plugins.

        Calls .restoreSettings (if available) on all plugins."""
        # Loads any user defined plugin directories
        pluginPaths = self.app.settings.value("Plugins/Paths", [])

        for path in pluginPaths:
            self.loadPluginPath(str(path))

        # Runs any plugins that were saved to the settings
        openPlugins = self.app.settings.value("%s/Plugins_Opened" % self.name) or []
        if isinstance(openPlugins, str):
            openPlugins = [openPlugins]
        for plugin in openPlugins:
            if '::' in plugin:
                plugin_name, plugin_state = str(plugin).split("::")
                self.launchPlugin(plugin_name, plugin_state)

    def launchPlugin(self, plugin_name, plugin_state):
        """Launches the desired plugin.

        @param plugin_name: The name of the plugin as provided by PLUGIN_NAME
        @type  plugin_name: string
        @param plugin_state: The state of the plugin's tab
        @type  plugin_state: string"""
        try:
            plugin_class = self.__plugins[plugin_name][CLASS]
        except KeyError:
            logger.warning(
                "Unable to launch previously open plugin, it no longer exists: %s", plugin_name)
            return

        # pylint: disable=broad-except
        try:
            plugin_instance = plugin_class(self.mainWindow)
            self.__running.append((plugin_name, plugin_instance))
            plugin_instance.closed.connect(self.__closePlugin, QtCore.Qt.QueuedConnection)
        except Exception:
            logger.warning(
                "Failed to load plugin module: %s\n%s",
                plugin_name, ''.join(traceback.format_exception(*sys.exc_info())))
            return

        if hasattr(plugin_instance, "pluginRestoreState"):
            # pylint: disable=broad-except
            try:
                try:
                    if plugin_state:
                        # Earlier versions of CueGUI saved data via pickle; fall back to that if
                        # valid JSON is not found.
                        try:
                            state = json.loads(plugin_state)
                        except JSON_EXCEPTION_CLASS:
                            # Python 2 doesn't support the same bytes() options, but that's ok
                            # because the pickled data is already in the format we need.
                            try:
                                state = pickle.loads(bytes(plugin_state, encoding='latin1'))
                            except TypeError:
                                state = pickle.loads(plugin_state)
                    else:
                        state = None
                except Exception as e:
                    logger.warning(
                        "Failed to load state information stored as %s for %s, error was: %s",
                        plugin_state, plugin_name, e)
                    state = None
                plugin_instance.pluginRestoreState(state)
            except Exception as e:
                logger.warning("Error restoring plugin state for: %s", plugin_name)
                list(map(logger.warning, cuegui.Utils.exceptionOutput(e)))

    def loadPluginPath(self, plugin_dir):
        """This will load all plugin modules located in the path provided
        @param plugin_dir: Path to a plugin directory
        @type  plugin_dir: string"""

        if plugin_dir in self._loadedPaths:
            return
        self._loadedPaths.append(plugin_dir)

        if os.path.isdir(plugin_dir):
            orig_sys_path = sys.path[:]
            sys.path.append(plugin_dir)

            for p in os.listdir(plugin_dir):
                name, ext = os.path.splitext(p)
                if ext == ".py" and not name in ["__init__", "Manifest", "README"]:
                    self.loadPlugin(name)
            sys.path = orig_sys_path
        else:
            logger.warning("Unable to read the plugin path: %s", plugin_dir)

    def loadPlugin(self, name):
        """Loads a single plugin that must be in the python path
        @param name: Name of the python module that contains a plugin
        @type  name: string"""
        # pylint: disable=broad-except
        try:
            logger.info("Importing: %s", name)
            module = __import__(name, globals(), locals())
            logger.info("Has:      %s", dir(module))
            logger.info("Name:     %s", module.PLUGIN_NAME)
            logger.info("Provides: %s", module.PLUGIN_PROVIDES)

            # If a plugin requires a different app, do not use it
            # TODO: accept a list also, log it
            if hasattr(module, "PLUGIN_REQUIRES"):
                if self.mainWindow.app_name != module.PLUGIN_REQUIRES:
                    return

            newPlugin = {}
            newPlugin[CLASS] = getattr(module, module.PLUGIN_PROVIDES)
            newPlugin[DESCRIPTION] = str(module.PLUGIN_DESCRIPTION)

            if hasattr(module, "PLUGIN_CATEGORY"):
                newPlugin[CATEGORY] = str(module.PLUGIN_CATEGORY)

            self.__plugins[module.PLUGIN_NAME] = newPlugin

        except Exception:
            logger.warning(
                "Failed to load plugin %s\n%s",
                name, ''.join(traceback.format_exception(*sys.exc_info())))

    def setupPluginMenu(self, menu):
        """Adds a plugin menu option to the supplied menubar
        @param menu: The menu to add the loaded plugins to
        @type  menu: QMenu"""
        menu.triggered.connect(self._handlePluginMenu)

        # Create the submenus (ordered)
        submenus = {}
        menu_locations = {"root": []}
        plugin_categories = {
            plugin[CATEGORY] for plugin in list(self.__plugins.values()) if CATEGORY in plugin}
        for category in plugin_categories:
            submenus[category] = QtWidgets.QMenu(category, menu)
            menu.addMenu(submenus[category])
            menu_locations[category] = []

        # Store the plugin name in the proper menu_locations category
        # pylint: disable=consider-using-dict-items
        for plugin in self.__plugins:
            category = self.__plugins[plugin].get(CATEGORY, "root")
            menu_locations[category].append(plugin)

        # Create the QAction and add it to the correct menu (sorted)
        # pylint: disable=consider-using-dict-items
        for category in menu_locations:
            for plugin in sorted(menu_locations[category]):
                action = QtWidgets.QAction("{}".format(plugin), menu)
                if category in submenus:
                    submenus[category].addAction(action)
                else:
                    menu.addAction(action)

        return menu

    def _handlePluginMenu(self, action):
        """Handles what happens when a plugin menu item is clicked on
        @param action: The action that was selected from the menu
        @type  action: QAction"""
        plugin_name = str(action.text()).split("%s" % self.__menu_separator, maxsplit=1)[0]
        self.launchPlugin(plugin_name, "")


class Plugin(object):
    """Represents a single plugin."""

    def __init__(self):
        self.__settings = []
        self.app = cuegui.app()

    def pluginRestoreState(self, saved_settings):
        """Called on plugin start with any previously saved state.

        @param saved_settings: Last state of the plugin instance
        @type  saved_settings: dict"""
        if self.__settings and saved_settings and isinstance(saved_settings, dict):
            for setting in self.__settings:
                item = setting[SETTINGS_KEY]
                if item in saved_settings:
                    setting[SETTINGS_SET](saved_settings[item])

    def pluginSaveState(self):
        """Called on application exit and returns plugin state information.
        @return: Any object to store as the current state of the plugin instance
        @rtype:  any"""
        save = {}
        if self.__settings:
            for setting in self.__settings:
                save[setting[SETTINGS_KEY]] = setting[SETTINGS_GET]()
        return save

    def pluginRegisterSettings(self, settings):
        """Stores the available settings.
        @param settings: a list of tuples that contain the settings key, the
                         callable to get the setting and a callable that takes
                         the setting.
        @type settings: list<tuple>"""
        self.__settings = settings
