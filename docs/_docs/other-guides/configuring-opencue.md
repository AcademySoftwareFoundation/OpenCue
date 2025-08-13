---
title: "Configuring OpenCue"
layout: default
parent: Other Guides
nav_order: 28
linkTitle: "Configuring OpenCue"
date: 2023-01-26
description: >
  Configure OpenCue with custom settings for your environment
---

# Configuring OpenCue

### Configure OpenCue with custom settings for your environment

---

This guide describes how to customize OpenCue's configuration settings for your environment.

## Cuebot

The available Cuebot settings are defined in
[`opencue.properties`](https://github.com/AcademySoftwareFoundation/OpenCue/blob/master/cuebot/src/main/resources/opencue.properties).

All of these settings can be overridden via commandline flags:

```
java -jar cuebot.jar \
  --datasource.cue-data-source.jdbc-url=jdbc:postgresql://my_database_host/cuebot_db_name \
  --datasource.cue-data-source.username=my_db_user \
  --datasource.cue-data-source.password=my_db_pass \
  --log.frame-log-root.default_os="/path/to/logs"
```

Alternatively, settings can be overridden via environment variables:

```
export datasource_cue_data_source_jdbc_url=jdbc:postgresql://my_database_host/cuebot_db_name
export datasource_cue_data_source_username=my_db_user
export datasource_cue_data_source_password=my_db_pass
export log_frame_log_root_default_os="/path/to/log"
java -jar cuebot.jar
```

Note that environment variable names have all dashes (`-`) and dots (`.`) replaced by underscores.

## RQD

The available RQD settings are defined in
[`rqconstants.py`](https://github.com/AcademySoftwareFoundation/OpenCue/blob/master/rqd/rqd/rqconstants.py).

This file defines several settings; look for the phrase `config.has_option` to see the settings
that may be overridden.

Override settings by creating a file `rqd.conf`:

* On Linux, `/etc/opencue/rqd.conf`
* On Windows, `%LOCALAPPDATA%/OpenCue/rqd.conf`

You may also specify your own custom path via the `-c` flag:

```
rqd -c /path/to/my/rqd.conf
```

`rqd.conf` should contain an `[Override]` heading followed by any settings you wish to override:

```
[Override]
RQD_BECOME_JOB_USER=false
```

Restart RQD to have the new settings take effect.

## GUI and Python tools

### Shared config directory

All of these tools share a single directory where configuration may be stored:

* On Windows, `%APPDATA%/opencue` (typically `C:/Users/<username>/AppData/Roaming/opencue`)
* On macOS and Linux, `~/.config/opencue`

Create this directory if it does not already exist.

### opencue module

The `opencue` module contains the main OpenCue Python API. Its settings will be inherited
by any of the other tools that utilize the OpenCue Python API, like CueGUI and the `cueadmin`
tool.

[`default.yaml`](https://github.com/AcademySoftwareFoundation/OpenCue/blob/master/pycue/opencue/default.yaml)
lists all default settings and provides an example for your own file.

To override these settings, create a file `opencue.yaml` following the same format.

This file may be stored in:
* the [shared config directory](#shared-config-directory)
* or at a path of your choosing, specified via the `OPENCUE_CONFIG_FILE` environment variable.

### outline module

The `outline` module contains a library for constructing OpenCue jobs. Its settings will
be inherited by any other tools that utilize that library, such as the CueSubmit tool.

[`outline.cfg`](https://github.com/AcademySoftwareFoundation/OpenCue/blob/master/pyoutline/etc/outline.cfg)
lists default settings and provides an example for your own file.

To override these settings, create a file `outline.cfg` following the same format.

This file may be stored in:
* the [shared config directory](#shared-config-directory)
* or at a path of your choosing, specified via the `OUTLINE_CONFIG_FILE` environment variable.

### CueGUI

[`cuegui.yaml`](https://github.com/AcademySoftwareFoundation/OpenCue/blob/master/cuegui/cuegui/config/cuegui.yaml)
lists default CueGUI settings and provides an example for your own file.

To override these settings, create a file `cuegui.yaml` following the same format.

This file may be stored in:
* the [shared config directory](#shared-config-directory)
* or at a path of your choosing, specified via the `CUEGUI_CONFIG_FILE` environment variable.

### CueSubmit

[`cuesubmit_config.example.yaml`](https://github.com/AcademySoftwareFoundation/OpenCue/blob/master/cuesubmit/cuesubmit_config.example.yaml)
lists default CueSubmit settings and provides an example for your own file.

To override these settings, create a file `cuesubmit.yaml` following the same format.

This file may be stored in:
* the [shared config directory](#shared-config-directory)
* or at a path of your choosing, specified via the `CUESUBMIT_CONFIG_FILE` environment variable.

### cueadmin

The `cueadmin` commandline tool does not utilize any additional settings beyond what is configured
by the [`opencue` module](#opencue-module).
