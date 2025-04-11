# CueGUI Plugins

This folder contains **optional plugins for CueGUI**. Plugins can add new menu actions, custom UI components, visualizations, and more - all without modifying CueGUI's core source code.

## Contents
- [Plugin structure](#plugin-structure)
  - [Example of plugin folder structure](#example-of-plugin-folder-structure)
- [Plugin loading](#plugin-loading)
- [Adding a new plugin](#adding-a-new-plugin)
- [List of plugins](#list-of-plugins)
  - [1) cueprogbar](#1-cueprogbar)
    - [How to use?](#how-to-use)
    - [Standalone Mode (CLI)](#standalone-mode-cli)
- [Notes](#notes)
- [Tips](#tips)


## Plugin structure

Each plugin lives in its own subfolder under `cueguiplugin/`, and should contain the following:

- `plugin.py`: Defines a `Plugin` class that implements the plugin interface.
- `config.yaml` (optional): Used to configure menu labels, enable/disable status, icons, or behavior.
- Additional supporting files (e.g., plugin code and logic, icons, so on).

Go back to [Contents](#contents).

### Example of plugin folder structure

```
cueguiplugin/
├── README.md
├── __init__.py                # Plugin interface definition
├── loader.py                  # Plugin discovery and loading
└── cueprogbar/                # Example plugin
    ├── __init__.py
    ├── __main__.py            # For standalone use (CLI)
    ├── config.yaml            # Plugin-specific config (label, icon, etc.)
    ├── darkmojo.py            # Custom dark UI palette
    ├── images/
    │   └── cueprogbar_icon.png
    ├── main.py                # Widget logic
    └── plugin.py              # Plugin class entrypoint
```

Go back to [Contents](#contents).

## Plugin loading

Plugins are dynamically loaded using `cueguiplugin/loader.py`, and automatically integrated into:
- MenuAction.py
- JobMonitorTree.py
- CueJobMonitorTree.py

There's no need to modify CueGUI itself. To add a plugin, just drop it into this folder and it will be picked up at runtime.
Global plugin control is defined via `.cueguipluginrc.yaml` in this directory.

Go back to [Contents](#contents).

## Adding a new plugin

1. Create a new folder inside `cueguiplugin/`, for example:

```bash
mkdir cueguiplugin/myplugin
```

2. Add a plugin.py with the following structure:

```python
from qtpy.QtWidgets import QAction

class Plugin:
    def __init__(self, job, parent=None, config=None):
        self._job = job
        self._parent = parent
        self._config = config or {}

    def menuAction(self):
        action = QAction("My Plugin Action", self._parent)
        action.triggered.connect(self.run)
        return action

    def run(self):
        print(f"Running plugin for job: {self._job.name()}")
```

3. Optionally, add a `config.yaml` to define:

```yaml
enabled: true
menu_label: My Plugin Action
icon: images/my_icon.png
```

Go back to [Contents](#contents).

## List of plugins

### 1) `cueprogbar`

The cueprogbar plugin adds a visual job progress bar for OpenCue jobs. It provides real-time color-coded frame status and basic job control.

Go back to [Contents](#contents).

#### How to use?

1. Open Cuetopia or Cuecommander from CueGUI.
2. Right-click on any job listed.
3. Select "Show Progress Bar" from the context menu.

This opens a small floating window with:

- A real-time progress bar (color-coded by frame state)
- Labels with job info and progress summary
- Right-click actions to:
  - Pause / Unpause the job
  - Kill the job
- Left-click to view a breakdown of frame states (SUCCEEDED, RUNNING, WAITING, DEPEND, DEAD, EATEN)

Go back to [Contents](#contents).

#### Standalone Mode (CLI)

You can also launch the plugin directly:

```bash
cd OpenCue/
python -m cuegui.cueguiplugin.cueprogbar <job_name>
```

Example:

```bash
python -m cuegui.cueguiplugin.cueprogbar testing-test_shot-my_render_job
```

This is useful for testing or display CueGUI plugins outside of CueGUI.

Go back to [Contents](#contents).

## Notes

- All plugins must be Python 3 compatible.
- Qt compatibility is maintained via qtpy (supports PySide2, PyQt5, etc.).

Go back to [Contents](#contents).

## Tips

- You can disable or enable plugins centrally via `.cueguipluginrc.yaml`
- Each plugin can have its own `config.yaml` for UI and behavior customization
- Use `darkmojo.py` if you want a consistent dark theme for all plugin UIs

Go back to [Contents](#contents).
