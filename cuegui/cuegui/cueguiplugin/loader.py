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
Dynamic plugin loader for CueGUI

This module is responsible for dynamically discovering, loading, and initializing
CueGUI plugins defined inside the `cueguiplugin/` directory. Each plugin must
follow a specific structure and optionally support configuration via YAML files.

Features:
---------
- Automatically loads plugins from subfolders inside `cueguiplugin/`
- Reads global plugin control from `.cueguipluginrc.yaml`
- Ensures loaded plugins implement the required `Plugin` class

Expected Folder Structure:
--------------------------
cueguiplugin/
├── loader.py
├── .cueguipluginrc.yaml       # Global plugin control
├── cueprogbar/                # Plugin folder
│   ├── plugin.py              # Required: contains Plugin class
│   └── config.yaml            # Optional: plugin-specific config
│   └── Plugin code and logic
├── otherplugin1/
│   ├── plugin.py
│   └── config.yaml
│   └── Plugin code and logic
...
"""

import os
import importlib
import traceback
import yaml

# Path to this plugin root directory
PLUGIN_DIR = os.path.dirname(__file__)

# Optional global config file to control enabled/disabled plugins
GLOBAL_CONFIG_FILE = os.path.join(PLUGIN_DIR, ".cueguipluginrc.yaml")


def load_plugins(job, parent=None):
    """
    Load and initialize all enabled plugins for a given job and UI parent.

    Args:
        job: The job instance (passed to each plugin).
        parent: The QWidget parent (usually the CueGUI context menu parent).

    Returns:
        List of instantiated plugin objects implementing the `menuAction()` method.
    """
    plugins = []

    # Load global control config if available
    global_config = {}
    if os.path.isfile(GLOBAL_CONFIG_FILE):
        try:
            with open(GLOBAL_CONFIG_FILE, "r", encoding="utf-8") as f:
                global_config = yaml.safe_load(f) or {}
        except Exception as e:
            print(f"[PluginLoader] Failed to load global config: {e}")

    enabled_plugins = set(global_config.get("enabled_plugins", []))
    disabled_plugins = set(global_config.get("disabled_plugins", []))

    # Use whitelist logic if 'enabled_plugins' is explicitly defined, even if it's empty
    use_whitelist = "enabled_plugins" in global_config

    # Iterate over each folder in cueguiplugin/
    for folder in os.listdir(PLUGIN_DIR):
        full_path = os.path.join(PLUGIN_DIR, folder)
        plugin_file = os.path.join(full_path, "plugin.py")
        config_path = os.path.join(full_path, "config.yaml")

        # Skip if not a valid plugin folder (must contain plugin.py)
        if not os.path.isdir(full_path) or not os.path.isfile(plugin_file):
            continue

        # Enforce central control via .cueguipluginrc.yaml
        if use_whitelist and folder not in enabled_plugins:
            print(f"[PluginLoader] Skipping '{folder}' (not in enabled_plugins list)")
            continue
        if folder in disabled_plugins:
            print(f"[PluginLoader] Skipping '{folder}' (explicitly disabled)")
            continue

        # Load local plugin config.yaml if it exists
        plugin_config = {}
        if os.path.isfile(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    plugin_config = yaml.safe_load(f) or {}
            except Exception as e:
                print(f"[PluginLoader] Failed to read config.yaml for '{folder}': {e}")

        # Try importing the plugin class and instantiating it
        try:
            # Use relative import based on the current package name
            package = __package__
            module_name = f"{package}.{folder}.plugin"
            plugin_module = importlib.import_module(module_name)
            plugin_class = getattr(plugin_module, 'Plugin', None)

            if plugin_class:
                instance = plugin_class(job=job, parent=parent, config=plugin_config)
                plugins.append(instance)
            else:
                print(f"[PluginLoader] No 'Plugin' class found in '{module_name}'")

        except Exception as e:
            print(f"[PluginLoader] Failed to load plugin '{folder}': {e}")
            traceback.print_exc()

    return plugins
