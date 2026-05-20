---
title: "PyOutline API Reference"
nav_order: 73
parent: Reference
layout: default
date: 2026-03-13
description: >
  Complete API reference for PyOutline classes, methods, and modules.
---

# PyOutline API Reference

Complete reference for all PyOutline classes, methods, and constants.

> **Note:** PyOutline is the job definition library; [pycuerun](/docs/reference/commands/pycuerun/) is the CLI tool that launches PyOutline jobs. The `outline.cuerun` module listed below provides the programmatic bridge between them.

## outline.Outline

The top-level job definition container.

### Constructor

```python
Outline(name, frame_range=None, **args)
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | `str` | Job name |
| `frame_range` | `str` | Default frame range for all layers |
| `show` | `str` | Show name (default: `$SHOW`) |
| `shot` | `str` | Shot name (default: `$SHOT`) |
| `user` | `str` | Username (default: `$USER`) |
| `facility` | `str` | Target facility |
| `maxcores` | `float` | Maximum cores for the job |
| `maxgpus` | `int` | Maximum GPUs for the job |

### Layer Management

| Method | Description |
|--------|-------------|
| `add_layer(layer)` | Add a layer to the outline |
| `remove_layer(layer)` | Remove a layer from the outline |
| `get_layer(name)` | Get a layer by name |
| `get_layers()` | Get all layers |
| `is_layer(name)` | Check if a layer exists |

### Properties

| Method | Description |
|--------|-------------|
| `get_name()` | Get the job name |
| `set_name(name)` | Set the job name |
| `get_show()` | Get the show name |
| `get_shot()` | Get the shot name |
| `get_user()` | Get the username |
| `get_facility()` | Get the target facility |
| `set_facility(facility)` | Set the target facility |
| `get_maxcores()` | Get maximum cores |
| `set_maxcores(cores)` | Set maximum cores |

### Frame Range

| Method | Description |
|--------|-------------|
| `get_frame_range()` | Get the default frame range |
| `set_frame_range(range)` | Set the default frame range |

### Environment

| Method | Description |
|--------|-------------|
| `set_env(key, value)` | Set an environment variable |
| `get_env(key)` | Get an environment variable |

### Arguments

| Method | Description |
|--------|-------------|
| `set_arg(key, value)` | Set a custom argument |
| `get_arg(key)` | Get a custom argument |

### Session

| Method | Description |
|--------|-------------|
| `get_session()` | Get the associated Session object |
| `put_file(path, rename=None)` | Store a file in the session |
| `get_file(name)` | Get a file from the session |
| `put_data(key, data, force=False)` | Store data in the session |
| `get_data(key)` | Retrieve data from the session |

### Lifecycle

| Method | Description |
|--------|-------------|
| `setup()` | Prepare the outline for launch (INIT → SETUP → READY) |

---

## outline.Layer

Base class for all outline modules.

### Constructor

```python
Layer(name, **args)
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | `str` | Layer name |
| `range` | `str` | Frame range |
| `chunk` | `int` | Chunk size (frames per task) |
| `threads` | `float` | Number of threads |
| `threadable` | `bool` | Whether the layer can use multiple threads |
| `command` | `list` | Command to execute |
| `type` | `str` | Layer type: `Render`, `Util`, or `Post` |

### Arguments

| Method | Description |
|--------|-------------|
| `get_arg(key)` | Get an argument value |
| `set_arg(key, value)` | Set an argument value |
| `require_arg(key, type=None)` | Declare a required argument with optional type check |
| `get_args()` | Get all arguments as a dictionary |

### Frame Range

| Method | Description |
|--------|-------------|
| `get_frame_range()` | Get the layer's frame range |
| `set_frame_range(range)` | Set the layer's frame range |
| `set_chunk_size(size)` | Set the chunk size |
| `get_chunk_size()` | Get the chunk size |
| `get_local_frame_set(start)` | Get frames for a chunk starting at `start` |

### Dependencies

| Method | Description |
|--------|-------------|
| `depend_on(layer, type=None)` | Create a frame-by-frame dependency (or specify type) |
| `depend_all(layer)` | Create a layer-on-layer dependency |
| `depend_previous(layer)` | Create a previous-frame dependency |
| `get_depends()` | Get all dependencies |

### Children

| Method | Description |
|--------|-------------|
| `add_child(layer)` | Add a child layer (pre/post process) |
| `get_children()` | Get all child layers |

### Environment

| Method | Description |
|--------|-------------|
| `set_env(key, value)` | Set a layer environment variable |
| `get_env(key)` | Get a layer environment variable |
| `get_envs()` | Get all environment variables |

### Session I/O

| Method | Description |
|--------|-------------|
| `put_file(path, rename=None)` | Copy a file into the session |
| `get_file(name)` | Get a file path from the session |
| `sym_file(path)` | Create a symlink in the session |
| `put_data(key, data, force=False)` | Store data in the session |
| `get_data(key)` | Retrieve data from the session |

### Execution Hooks (override in subclasses)

| Method | Description |
|--------|-------------|
| `_setup()` | Called during outline setup phase |
| `_execute(frames)` | Called to execute the layer for a list of frames |
| `_before_execute()` | Called before frame execution |
| `_after_execute()` | Called after frame execution |

### Events

| Method | Description |
|--------|-------------|
| `add_event_listener(event, callback)` | Register an event listener |
| `get_event_handler()` | Get the EventHandler instance |

### Other

| Method | Description |
|--------|-------------|
| `get_name()` | Get the layer name |
| `set_name(name)` | Set the layer name |
| `get_outline()` | Get the parent Outline |
| `setup()` | Run setup phase |
| `execute(frame)` | Execute a specific frame |

---

## outline.Frame

A single-frame layer. Extends `Layer`.

```python
Frame(name, **args)
```

Always has exactly one frame. Immune from frame range intersection with the outline's range.

---

## outline.LayerPreProcess

Runs before the parent layer. Extends `Frame`.

```python
LayerPreProcess(creator, **args)
```

`creator` is the parent layer. The preprocess layer is auto-named
`{creator_name}_preprocess` (or custom `suffix`), automatically set as a utility
layer, and configured with a dependency to run before the parent layer unlocks.
Outputs stored via `put_data()` are available to the parent layer.

---

## outline.LayerPostProcess

Runs after the parent layer completes. Extends `Frame`.

```python
LayerPostProcess(name, **args)
```

---

## outline.OutlinePostCommand

Runs after the entire job completes. Extends `Frame`.

```python
OutlinePostCommand(name, **args)
```

Layer type is always `POST`.

---

## outline.modules.shell

### Shell

Execute a command over a frame range.

```python
Shell(name, **args)
```

| Argument | Type | Description |
|----------|------|-------------|
| `command` | `list[str]` | Command and arguments. Use `#IFRAME#` for frame number. |

### ShellSequence

Execute an array of commands (one per frame).

```python
ShellSequence(name, **args)
```

| Argument | Type | Description |
|----------|------|-------------|
| `commands` | `list[str]` | Array of commands, mapped to frames. |

### ShellCommand

Execute a single command (always one frame).

```python
ShellCommand(name, **args)
```

| Argument | Type | Description |
|----------|------|-------------|
| `command` | `list[str]` | Command and arguments. |

### ShellScript

Execute a script file.

```python
ShellScript(name, **args)
```

| Argument | Type | Description |
|----------|------|-------------|
| `script` | `str` | Path to the script file. |

### PyEval

Execute inline Python code.

```python
PyEval(name, **args)
```

| Argument | Type | Description |
|----------|------|-------------|
| `code` | `str` | Python code to execute. |

### shell() Factory

```python
shell(name, command, **args)
```

Convenience function to create a Shell layer.

---

## outline.depend

### DependType

Dependency type enumeration:

| Value | Description |
|-------|-------------|
| `DependType.FrameByFrame` | Each frame depends on the corresponding frame |
| `DependType.LayerOnLayer` | All frames depend on all frames |
| `DependType.PreviousFrame` | Each frame depends on the previous frame |
| `DependType.LayerOnSimFrame` | Simulation-specific dependency |
| `DependType.LayerOnAny` | Any frame completion satisfies the dependency |

### Depend

```python
Depend(depend_er, depend_on, type)
```

| Attribute | Description |
|-----------|-------------|
| `get_depend_er()` | The dependent layer |
| `get_depend_on()` | The dependency layer |
| `get_type()` | The dependency type |

---

## outline.Session

### Constructor

```python
Session(outline)
```

### Methods

| Method | Description |
|--------|-------------|
| `put_file(path, layer=None, rename=None)` | Copy file into session |
| `get_file(name, layer=None)` | Get file path from session |
| `sym_file(path, layer=None)` | Create symlink in session |
| `put_data(key, data, layer=None, force=False)` | Store serialized data |
| `get_data(key, layer=None)` | Retrieve serialized data |
| `get_path(layer=None)` | Get session directory path |
| `save()` | Save session state |

---

## outline.cuerun

### launch()

```python
launch(ol, use_pycuerun=True, **args)
```

Convenience function to launch an outline.

| Parameter | Type | Description |
|-----------|------|-------------|
| `ol` | `Outline` | The outline to launch |
| `use_pycuerun` | `bool` | Wrap commands with pycuerun (default: True) |
| `pause` | `bool` | Launch paused |
| `wait` | `bool` | Block until complete |
| `test` | `bool` | Block and fail on error |
| `range` | `str` | Override frame range |
| `facility` | `str` | Target facility |
| `backend` | `str` | Backend name |
| `nomail` | `bool` | Disable email |
| `maxretries` | `int` | Max retries per frame |
| `os` | `str` | Target OS |

### execute_frame()

```python
execute_frame(script, layer, frame)
```

Execute a single frame from an outline script.

### OutlineLauncher

```python
OutlineLauncher(outline, **args)
```

| Method | Description |
|--------|-------------|
| `set_flag(key, value)` | Set a launch flag |
| `get_flag(key)` | Get a launch flag |
| `setup()` | Prepare outline for launch |
| `launch(use_pycuerun=True)` | Submit the job |
| `serialize()` | Generate job specification |

---

## outline.event

### Event Types

| Event | When |
|-------|------|
| `LayerEvent.AFTER_INIT` | After layer initialization |
| `LayerEvent.AFTER_PARENTED` | After layer is added to outline |
| `LayerEvent.SETUP` | During setup phase |
| `LayerEvent.BEFORE_EXECUTE` | Before frame execution |
| `LayerEvent.AFTER_EXECUTE` | After frame execution |
| `LaunchEvent.BEFORE_LAUNCH` | Before job submission |
| `LaunchEvent.AFTER_LAUNCH` | After job submission |

---

## outline.io.FileSpec

```python
FileSpec(path)
```

Image sequence file specification with frame expansion.

| Method | Description |
|--------|-------------|
| `get_path()` | Get the base file path |
| `get_frame_path(num)` | Get path for a specific frame number |
| `exists()` | Check if the file exists |

---

## outline.constants

| Constant | Value | Description |
|----------|-------|-------------|
| `OUTLINE_MODE_INIT` | `0` | Parsing phase |
| `OUTLINE_MODE_SETUP` | `1` | Setup phase |
| `OUTLINE_MODE_READY` | `2` | Ready for launch |
| `FRAME_RANGE_FIRST` | `"first"` | First frame only |
| `FRAME_RANGE_LAST` | `"last"` | Last frame only |

### LayerType Enum

| Value | Description |
|-------|-------------|
| `LayerType.RENDER` | Primary rendering work |
| `LayerType.UTIL` | Utility tasks |
| `LayerType.POST` | Post-job tasks |

---

## outline.exception

| Exception | Description |
|-----------|-------------|
| `OutlineException` | Base exception for all PyOutline errors |
| `LayerException` | Layer-specific errors |
| `SessionException` | Session storage errors |
| `ShellCommandFailureException` | Shell command execution failures |
| `FailImmediately` | Force immediate frame failure (used by plugins) |
| `FileSpecException` | File specification errors |

---

## outline.util

| Function | Description |
|----------|-------------|
| `make_frame_set(range)` | Parse a frame range string into a set |
| `disaggregate_frame_set(frame_set)` | Expand a frame set into individual frames |
| `intersect_frame_set(set1, set2)` | Intersect two frame sets |
| `get_slice(items, range)` | Extract items for a frame range |
| `get_show()` | Get current show from environment |
| `get_shot()` | Get current shot from environment |
| `get_user()` | Get current username |
| `get_uid()` | Get current user ID |
