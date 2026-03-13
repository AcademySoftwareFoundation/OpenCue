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
Open Job Description (OpenJD) backend module.

Serializes a PyOutline job into an OpenJD 2023-09 Job Template (YAML).
This backend is intended for evaluation and interoperability with the
OpenJD ecosystem.  Jobs can be run locally via the ``openjd`` CLI, or
submitted to render management systems that consume OpenJD templates
such as AWS Deadline Cloud.

Unlike the ``cue`` backend this module does **not** submit to a remote
scheduler.  ``serialize()`` produces the template document and
``launch()`` runs the job locally via the ``openjd run`` CLI
(requires the ``openjd-cli`` package — install with
``pip install opencue-pyoutline[openjd]``).

See outline.backend.__init__.py for a description of the PyOutline backend
system.

Feature parity with the cue backend
====================================

Supported:

  Job definition (maps to OpenJD template):
  - Job name
  - Layer → Step mapping (skip unregistered, skip children, skip empty ranges)
  - Frame range + chunk size → parameterSpace (CHUNK[INT] task parameter)
  - Token replacement (#IFRAME#, #FRAMESPEC#, #FRAME_START#, #FRAME_END#,
    #FRAME_CHUNK#, #ZFRAME#, #JOB#, #LAYER#, #FRAME#)
  - Layer-on-layer dependencies (deduplicated per target step)
  - Host requirements: cores/threads, memory, gpus, gpu_memory, tags,
    service, limits, os
  - Layer env vars → stepEnvironments
  - Job-level env vars + launcher env → jobEnvironments
  - Job metadata (facility, show, shot, user) → job parameters
  - timeout → onRun action timeout (seconds)
  - Layer type Post → step with dependsOn all non-Post steps
  - Shell, ShellScript, ShellCommand, PyEval layer types
  - LayerPreProcess / LayerPostProcess (auto-wired as separate steps)

Missing / lossy (job definition gaps):
  - Dependency types: FrameByFrame, PreviousFrame, LayerOnSimFrame, and
    LayerOnAny are all collapsed into a flat dependsOn.  OpenJD only models
    step-on-step dependencies (all tasks must complete), so frame-level
    dependency granularity is lost.  Tracked upstream:
    https://github.com/OpenJobDescription/openjd-specifications/discussions/82
  - timeout_llu (Last Layer Update): the maximum time a frame can go without
    producing any output before being considered hung.  OpenJD has no
    equivalent — its timeout is wall-clock only.
    TODO: open a discussion on openjd-specifications for an inactivity-based
    timeout (similar to timeout_llu).
  - Layer outputs: the cue backend (spec >= 1.15) serializes get_outputs().
    Not yet mapped.  OpenJD PATH parameters support dataFlow but only at
    the job level, not per-step or per-task.
    TODO: open a discussion on openjd-specifications for step- and task-level
    file dataflow declarations (output path registration, existence checks).
  - Composite layers (parent-child grouping): child layers run sequentially
    within the parent's task, not as independent steps.  Currently skipped.
    TODO: serialize composite layers as a single step whose script runs
    the parent and children in sequence.  Sequential actions in onRun
    (https://github.com/OpenJobDescription/openjd-specifications/discussions/97)
    would allow each child to have its own timeout and cancellation behavior.
  - ShellSequence layer type (array of commands in one layer).  Sequential
    actions in onRun would enable this:
    https://github.com/OpenJobDescription/openjd-specifications/discussions/97

Not mapped (scheduling concerns, not job definition):
  OpenJD templates define job structure and commands, not scheduling policy.
  These are handled by the scheduler (e.g. OpenCue's cuebot, Deadline Cloud).
  - pause: launch job in paused state
  - priority: job priority for dispatch ordering
  - maxretries: max frame retry count on failure
  - autoeat: auto-consume failed frames
  - maxcores / maxgpus: job-level concurrency caps (max total cores/GPUs
    the job can consume simultaneously across all running frames)

Uncertain (could be either job definition or scheduling):
  - Layer type Render/Util: informational categorization used by OpenCue's
    filter system for bulk resource policy.  The actual resource requirements
    are already in hostRequirements, but the categorization itself could be
    useful metadata for a scheduler.
  - Threadable: per-layer flag indicating whether the application can use
    multiple cores.  Controls dynamic core scaling and bin-packing in
    OpenCue's dispatcher.  Could be job definition (it describes the
    application's behavior) or scheduling (it affects dispatch decisions).
    TODO: open a discussion on openjd-specifications about task-level
    metadata for core utilization (single-threaded vs multi-threaded) and
    how a scheduler could use it for concurrent task placement on a host.
"""

from __future__ import annotations

import logging
import os
import shlex
import subprocess
import tempfile
from typing import Any, Dict, List, Optional

import yaml

import outline
import outline.depend
import outline.exception
from openjd.model import DecodeValidationError, decode_job_template, escape_format_string

logger = logging.getLogger("outline.backend.openjd")

__all__ = [
    "launch",
    "serialize",
    "serialize_simple",
]

SPEC_VERSION = "jobtemplate-2023-09"
EXTENSIONS = ["TASK_CHUNKING", "EXPR"]


# ---------------------------------------------------------------------------
# Public backend interface (matches cue.py / local.py contract)
# ---------------------------------------------------------------------------


def launch(launcher, use_pycuerun=None):
    """Launch the job locally via ``openjd run``.

    Serializes the template to a temporary YAML file and invokes the
    openjd CLI to run the full job.  Requires the ``openjd-cli`` package
    to be installed (``pip install opencue-pyoutline[openjd]``).

    The *use_pycuerun* parameter is accepted for interface compatibility
    with other backends but has no effect — OpenJD templates always
    contain the commands directly.
    """
    template_yaml = serialize(launcher)

    # Write template to a temp file that persists until the run completes.
    tmp = tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".template.yaml",
        prefix="openjd-",
        delete=False,
        encoding="utf-8",
    )
    try:
        tmp.write(template_yaml)
        tmp.close()

        cmd = ["openjd", "run", tmp.name]

        logger.info("Running: %s", " ".join(cmd))
        result = subprocess.run(cmd, check=False, capture_output=True, text=True)

        if result.returncode != 0:
            raise outline.exception.OutlineException(
                "openjd run exited with code %d: %s" % (result.returncode, result.stderr)
            )
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass

    return template_yaml


def serialize(launcher):
    """Serialize the outline into an OpenJD job template YAML string."""
    return _serialize(launcher)


def serialize_simple(launcher):
    """Alias - OpenJD templates don't distinguish pycuerun wrapping."""
    return _serialize(launcher)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _frame_range_to_openjd(frame_range: str) -> str:
    """Convert a FileSequence-style frame range into an OpenJD IntRangeExpr.

    FileSequence uses ``1-10x2`` for step syntax while OpenJD uses ``1-10:2``.
    """
    return frame_range.replace("x", ":")


def _build_step_dependencies(layer) -> Optional[List[Dict[str, str]]]:
    """Return the ``dependencies`` list for a step, or *None* if empty."""
    deps = layer.get_depends()
    if not deps:
        return None
    seen = set()
    result: List[Dict[str, str]] = []
    for dep in deps:
        on_name = dep.get_depend_on_layer().get_name()
        if on_name not in seen:
            result.append({"dependsOn": on_name})
            seen.add(on_name)
    return result


def _map_os(os_name: str) -> tuple:
    """Map an OpenCue OS string to (os_family, distro).

    Returns a tuple of (family, distro) where family is one of the
    OpenJD ``attr.worker.os.family`` values (linux, windows, macos)
    and distro is an optional Linux distribution name for
    ``attr.linux.distro``, or None.
    """
    lower = os_name.lower()
    if lower in ("windows", "win32", "win64", "nt"):
        return ("windows", None)
    if lower in ("darwin", "macos"):
        return ("macos", None)
    if lower == "linux":
        return ("linux", None)
    # Distro-specific (centos7, rocky9, rhel7, etc.) → linux + distro
    return ("linux", lower)


def _build_host_requirements(layer, os_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Map PyOutline resource args to OpenJD ``hostRequirements``."""
    amounts: List[Dict[str, Any]] = []
    attributes: List[Dict[str, Any]] = []

    # OS → attr.worker.os.family (and optionally attr.linux.distro)
    if os_name:
        family, distro = _map_os(os_name)
        attributes.append({"name": "attr.worker.os.family", "anyOf": [family]})
        if distro:
            attributes.append({"name": "attr.linux.distro", "anyOf": [distro]})

    # CPU cores
    cores = None
    if layer.is_arg_set("cores"):
        cores = layer.get_arg("cores")
    elif layer.is_arg_set("threads"):
        cores = layer.get_arg("threads")
    if cores is not None:
        amounts.append({"name": "amount.worker.vcpu", "min": float(cores)})

    # Memory — PyOutline passes memory through as an opaque string to cuebot,
    # which parses it via convertMemoryInput:
    #   "<number>m" → megabytes
    #   "<number>g" → gigabytes
    #   "<number>"  (no suffix) → gigabytes
    # We replicate that logic here and convert to MiB for OpenJD.
    memory = layer.get_arg("memory")
    if memory:
        mem_mib = _parse_memory_to_mib(str(memory))
        amounts.append({"name": "amount.worker.memory", "min": mem_mib})

    # GPUs
    gpus = layer.get_arg("gpus")
    if gpus:
        amounts.append({"name": "amount.worker.gpu", "min": int(gpus)})
    # GPU memory — same format as regular memory
    gpu_memory = layer.get_arg("gpu_memory")
    if gpu_memory:
        gpu_mem_mib = _parse_memory_to_mib(str(gpu_memory))
        amounts.append({"name": "amount.worker.gpu.memory", "min": gpu_mem_mib})

    # Tags → custom attribute opencue:attr.tag
    # Tags can be a pipe-delimited string ("render|gpu") or a list.
    tags = layer.get_arg("tags")
    if tags:
        tag_list = _parse_tags(tags)
        if tag_list:
            attributes.append({"name": "opencue:attr.tag", "allOf": tag_list})

    # Service → custom attribute opencue:attr.service
    # Match the cue backend which takes only the first comma-separated service
    # (see cue.py: layer.get_service().split(",")[0]).
    # TODO: consider using the full list as anyOf values, since OpenJD's anyOf
    # semantics ("host must have at least one") are a better fit for multiple
    # services than discarding all but the first.
    service = layer.get_service()
    if service:
        primary = service.split(",")[0].strip()
        if primary:
            attributes.append({"name": "opencue:attr.service", "anyOf": [primary]})

    # Limits → amount.limit.<name> (min: 1)
    # Each named limit is mapped as a consumable amount so that an
    # OpenJD-compatible scheduler (e.g. Deadline Cloud) can enforce
    # concurrency limits the same way OpenCue does.
    layer_limits = layer.get_limits()
    if layer_limits:
        for limit_name in layer_limits:
            amounts.append({"name": "amount.limit.%s" % limit_name, "min": 1})

    if not amounts and not attributes:
        return None
    req: Dict[str, Any] = {}
    if amounts:
        req["amounts"] = amounts
    if attributes:
        req["attributes"] = attributes
    return req


def _parse_tags(tags) -> List[str]:
    """Normalize tags from a pipe-delimited string or list into a clean list."""
    if isinstance(tags, str):
        return [t.strip() for t in tags.split("|") if t.strip()]
    if isinstance(tags, (list, tuple)):
        return [str(t).strip() for t in tags if str(t).strip()]
    return []


def _parse_memory_to_mib(value: str) -> int:
    """Convert a cuebot-style memory string to MiB for OpenJD.

    Follows cuebot's ``convertMemoryInput`` convention, which treats
    MB and MiB interchangeably (no 1000→1024 conversion):

      - ``"512m"``  → 512 MiB
      - ``"4g"``    → 4096 MiB  (value × 1024)
      - ``"4"``     → 4096 MiB  (plain number treated as GiB)

    Raises:
        LayerException: If the value cannot be parsed.
    """
    v = value.strip().lower()
    try:
        if v.endswith("m"):
            return int(float(v[:-1]))
        elif v.endswith("g"):
            return int(float(v[:-1]) * 1024)
        else:
            # Plain number — cuebot treats as gigabytes.
            return int(float(v) * 1024)
    except (ValueError, TypeError):
        raise outline.exception.LayerException(
            "Invalid memory value: %r — expected a number with optional "
            "'m' (megabytes) or 'g' (gigabytes) suffix" % value
        )



# Token replacement map for OpenCue → OpenJD.
# All steps use CHUNK[INT], so Task.Param.Frame is a range expression.
# min()/max() extract the first/last frame from the range.
_TOKENS = {
    "#FRAMESPEC#": "{{ Task.Param.Frame }}",
    "#IFRAME#": "{{ min(Task.Param.Frame) }}",
    "#ZFRAME#": "{{ zfill(min(Task.Param.Frame), 4) }}",
    "#FRAME_START#": "{{ min(Task.Param.Frame) }}",
    "#FRAME_END#": "{{ max(Task.Param.Frame) }}",
    "#FRAME_CHUNK#": "{{ chunk_size }}",
    "#JOB#": "{{ Job.Name }}",
    "#LAYER#": "{{ Step.Name }}",
    "#FRAME#": "{{ zfill(min(Task.Param.Frame), 4) }}-{{ Step.Name }}",
}


def _replace_tokens(value: str, token_map: dict) -> str:
    """Replace all OpenCue command tokens in a string."""
    for token, replacement in token_map.items():
        value = value.replace(token, replacement)
    return value


def _build_cue_env_exports() -> str:
    """Build the export lines for task-level CUE_* environment variables."""
    return (
        "export CUE_IFRAME={{ min(Task.Param.Frame) }}\n"
        "export CUE_JOB={{ repr_sh(Job.Name) }}\n"
        "export CUE_LAYER={{ repr_sh(Step.Name) }}\n"
        "export CUE_FRAME={{ repr_sh(zfill(min(Task.Param.Frame), 4)"
        " + '-' + Step.Name) }}\n"
    )


def _build_step_script(layer) -> Dict[str, Any]:
    """Build the ``script`` block for a step.

    All layer types are wrapped in a bash script that exports task-level
    CUE_* environment variables for compatibility, then runs the actual
    command.

    Handles three layer types:
      - ShellScript: embeds the script file, wrapper calls it.
      - PyEval: embeds the Python code, wrapper calls ``python`` on it.
      - Shell/ShellCommand/other: wrapper calls the command directly.
    """
    from outline.modules.shell import PyEval, ShellScript

    env_exports = _build_cue_env_exports()
    embedded_files: List[Dict[str, Any]] = []

    # Determine the command line to put in the wrapper.
    if isinstance(layer, ShellScript):
        script_path = layer.get_arg("script")
        with open(script_path, encoding="utf-8") as fp:
            script_content = fp.read()
        embedded_files.append(
            {"name": "script", "type": "TEXT", "runnable": True, "data": script_content}
        )
        cmd_line = "{{ repr_sh(Task.File.script) }}"

    elif isinstance(layer, PyEval):
        # PyEval stores code as a string in a private attribute with no public
        # getter.  It's available before _setup() clears it, and serialization
        # runs before setup.
        # TODO: add a public get_code() method to PyEval so backends don't
        # need to access the name-mangled attribute.
        code = layer._PyEval__code
        if code is None:
            raise outline.exception.LayerException(
                "PyEval layer '%s' has no code — was setup() already called?" % layer.get_name()
            )
        embedded_files.append({"name": "script", "type": "TEXT", "data": code})
        cmd_line = "python {{ repr_sh(Task.File.script) }}"

    else:
        # Shell/ShellCommand/other: resolve tokens in the command.
        command_parts = layer.get_arg("command") or layer.get_arg("cmd")
        if command_parts:
            if isinstance(command_parts, (list, tuple)):
                resolved = [_replace_tokens(str(part), _TOKENS) for part in command_parts]
            else:
                resolved = [
                    _replace_tokens(part, _TOKENS) for part in shlex.split(str(command_parts))
                ]
        else:
            raise outline.exception.LayerException(
                "Layer '%s' has no command set" % layer.get_name()
            )
        cmd_line = " ".join(shlex.quote(arg) for arg in resolved)

    # Build the wrapper script.
    wrapper = "#!/bin/bash\n"
    wrapper += env_exports
    # 'exec' replaces the wrapper shell with the actual command process,
    # so the session runner tracks the real PID for timeout/cancellation.
    wrapper += f"exec {cmd_line}\n"

    embedded_files.append({
        "name": "opencue_wrapper", "type": "TEXT", "runnable": True, "data": wrapper
    })

    action: Dict[str, Any] = {"command": "{{ Task.File.opencue_wrapper }}"}
    timeout = layer.get_arg("timeout")
    if timeout:
        action["timeout"] = int(timeout)

    result: Dict[str, Any] = {"actions": {"onRun": action}}
    if embedded_files:
        result["embeddedFiles"] = embedded_files
    return result


def _build_environment(layer, launcher) -> List[Dict[str, Any]]:
    """Build ``stepEnvironments`` from layer env vars and per-step CUE_* vars."""

    # Start with user-defined layer env vars.
    variables = {}
    envs = layer.get_envs()
    if envs:
        variables.update({str(k): escape_format_string(str(v)) for k, v in envs.items()})

    # Per-step CUE_* variables (these vary by layer).
    variables["CUE_RANGE"] = "{{ frames }}"
    variables["CUE_CHUNK"] = "{{ chunk_size }}"
    variables["CUE_THREADABLE"] = "1" if layer.get_arg("threadable") else "0"

    return [{"name": f"{layer.get_name()}-env", "variables": variables}]


def _serialize(launcher) -> str:
    """Core serialization: Outline → OpenJD 2023-09 Job Template dict → YAML."""
    ol = launcher.get_outline()

    # Collect eligible layers and partition into regular vs Post.
    # Post layers in OpenCue run in a separate job after the main job
    # completes.  In OpenJD we keep them in the same template and
    # inject dependsOn entries for every non-Post step.
    regular_layers = []
    post_layers = []
    for layer in ol.get_layers():
        if not layer.get_arg("register"):
            continue
        if layer.get_parent():
            continue
        frame_range = layer.get_frame_range()
        if not frame_range:
            logger.info("Skipping layer %s - frame range does not intersect job range", layer)
            continue
        if str(layer.get_type()) == "Post":
            post_layers.append(layer)
        else:
            regular_layers.append(layer)

    steps: List[Dict[str, Any]] = []
    non_post_step_names: List[str] = []

    for layer in regular_layers:
        step = _build_step(layer, launcher)
        steps.append(step)
        non_post_step_names.append(layer.get_name())

    for layer in post_layers:
        step = _build_step(layer, launcher, depends_on_all=non_post_step_names)
        steps.append(step)

    if not steps:
        raise outline.exception.OutlineException(
            "Failed to serialize job. No layers with valid frame ranges."
        )

    # Build the template dict in a human-friendly field order.
    job_name = launcher.get_flag("basename") or ol.get_name()
    template: Dict[str, Any] = {
        "name": escape_format_string(job_name),
        "specificationVersion": SPEC_VERSION,
    }

    template["extensions"] = EXTENSIONS

    # Job metadata as parameters — these map OpenCue launcher flags to
    # OpenJD job parameters so they can be overridden at submit time.
    template["parameterDefinitions"] = [
        {"name": "Facility", "type": "STRING", "default": launcher.get_flag("facility", "")},
        {"name": "Show", "type": "STRING", "default": ol.get_show() or ""},
        {"name": "Shot", "type": "STRING", "default": ol.get_shot() or ""},
        {"name": "User", "type": "STRING", "default": launcher.get_flag("user", "")},
    ]

    # Job-level environment variables
    job_environments: List[Dict[str, Any]] = []

    # CUE_* variables that are the same for every step.
    job_environments.append({"name": "cue-env", "variables": {
        "CUE3": "1",
        "CUE_SHOW": "{{ Param.Show }}",
        "CUE_SHOT": "{{ Param.Shot }}",
        "CUE_USER": "{{ Param.User }}",
    }})

    # User-defined job-level env vars from the outline and launcher.
    job_envs = ol.get_env()
    launcher_envs = launcher.get_flag("env") or []
    variables = {}
    if job_envs:
        for env_k, env_v in job_envs.items():
            # env_v is (value, pre_setshot_bool)
            variables[env_k] = escape_format_string(env_v[0])
    for kvp in launcher_envs:
        k, v = kvp.split("=", 1)
        variables[k] = escape_format_string(v)
    if variables:
        job_environments.append({"name": "outline-env", "variables": variables})

    template["jobEnvironments"] = job_environments

    template["steps"] = steps

    # Validate the template using openjd-model if available.
    _validate_template(template)

    return yaml.dump(template, default_flow_style=False, sort_keys=False, Dumper=_BlockDumper)


class _BlockDumper(yaml.SafeDumper):
    """YAML dumper that uses block scalar style (|) for multi-line strings."""


def _block_str_representer(dumper, data):
    if "\n" in data:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


_BlockDumper.add_representer(str, _block_str_representer)


def _validate_template(template: Dict[str, Any]) -> None:
    """Validate the generated template against the OpenJD model."""
    try:
        decode_job_template(
            template=template,
            supported_extensions=template.get("extensions"),
        )
    except DecodeValidationError as exc:
        raise outline.exception.OutlineException(
            "Generated OpenJD template failed validation: %s" % exc
        )


def _build_step(layer, launcher, depends_on_all: Optional[List[str]] = None) -> Dict[str, Any]:
    """Build a single OpenJD step dict from a PyOutline layer."""
    step: Dict[str, Any] = {"name": layer.get_name()}

    # Dependencies — merge explicit depends with implied Post dependencies.
    deps = _build_step_dependencies(layer)
    if depends_on_all:
        if deps is None:
            deps = []
        seen = {d["dependsOn"] for d in deps}
        for name in depends_on_all:
            if name not in seen:
                deps.append({"dependsOn": name})
                seen.add(name)
    if deps:
        step["dependencies"] = deps

    # Step-level let bindings — define frames and chunk_size once,
    # referenced by parameterSpace, stepEnvironments, and script.
    chunk_size = layer.get_chunk_size()
    openjd_range = _frame_range_to_openjd(layer.get_frame_range())
    step["let"] = [
        f'frames = range_expr("{openjd_range}")',
        f"chunk_size = {chunk_size}",
    ]

    # Step environments
    step_env = _build_environment(layer, launcher)
    if step_env:
        step["stepEnvironments"] = step_env

    # Parameter space
    step["parameterSpace"] = {"taskParameterDefinitions": [{
        "name": "Frame",
        "type": "CHUNK[INT]",
        "range": "{{ frames }}",
        "chunks": {
            "defaultTaskCount": "{{ chunk_size }}",
            "rangeConstraint": "CONTIGUOUS",
        },
    }]}

    # Script
    step["script"] = _build_step_script(layer)

    # Host requirements
    host_req = _build_host_requirements(layer, os_name=launcher.get_flag("os"))
    if host_req:
        step["hostRequirements"] = host_req

    return step
