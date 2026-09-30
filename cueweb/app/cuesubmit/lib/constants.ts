/*
 * Copyright Contributors to the OpenCue Project
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

// Mirrors cuesubmit/cuesubmit/Constants.py and JobTypes.py. Keeping the
// list narrow on purpose: cuesubmit also has "FROM_CONFIG_FILE" jobs
// pulled out of cuesubmit_config.yaml, which we don't load here.

export const JOB_TYPES = ["Shell", "Maya", "Nuke", "Blender"] as const;
export type JobType = (typeof JOB_TYPES)[number];

// Two-tier list because the cuesubmit UI renders an empty default so
// "no dependency" is a real choice on the first layer.
export const DEPENDENCY_TYPES = ["", "Layer", "Frame"] as const;
export type DependencyType = (typeof DEPENDENCY_TYPES)[number];

// Default service catalog drawn from the cuesubmit screenshots. Real
// deployments override this via cuesubmit_config.yaml; we expose it as
// a single list with a `default` first so the dropdown shows the same
// options the CueGUI submit dialog does.
export const DEFAULT_SERVICES = [
  "default",
  "prman",
  "arnold",
  "shell",
  "maya",
  "houdini",
  "katana",
  "nuke",
  "postprocess",
] as const;

// Built-in limits list - empty by default. cuesubmit_config.yaml at the
// studio level usually adds names here.
export const DEFAULT_LIMITS: ReadonlyArray<string> = [];

// Tokens recognized by cuebot at dispatch time. Shown in the
// command-help popover next to Frame Spec / Command To Run.
// Source of truth: cuesubmit/cuesubmit/Constants.py COMMAND_TOKENS.
export const COMMAND_TOKENS: ReadonlyArray<{ token: string; description: string }> = [
  { token: "#ZFRAME#", description: "Current frame, zero-padded to 4 digits" },
  { token: "#IFRAME#", description: "Current frame" },
  { token: "#FRAME_START#", description: "First frame of the chunk" },
  { token: "#FRAME_END#", description: "Last frame of the chunk" },
  { token: "#FRAME_CHUNK#", description: "Chunk size" },
  { token: "#FRAMESPEC#", description: "Full frame range" },
  { token: "#LAYER#", description: "Layer name" },
  { token: "#JOB#", description: "Job name" },
  { token: "#FRAME#", description: "Frame name" },
];

// Per-type render command stems. Match cuesubmit's defaults; operators
// can override these via cuesubmit_config.yaml on the studio side.
export const MAYA_RENDER_CMD = "Render";
export const NUKE_RENDER_CMD = "nuke";
export const BLENDER_RENDER_CMD = "blender";

// Frame tokens substituted by cuebot when dispatching a frame.
export const FRAME_TOKEN = "#IFRAME#";
export const FRAME_START_TOKEN = "#FRAME_START#";
export const FRAME_END_TOKEN = "#FRAME_END#";

// Blender -F output formats. Mirrors BLENDER_FORMATS in Constants.py
// (the leading "" represents "leave format unspecified").
export const BLENDER_FORMATS = [
  "",
  "AVIJPEG",
  "AVIRAW",
  "BMP",
  "CINEON",
  "DPX",
  "EXR",
  "HDR",
  "IRIS",
  "IRIZ",
  "JP2",
  "JPEG",
  "MPEG",
  "MULTILAYER",
  "PNG",
  "RAWTGA",
  "TGA",
  "TIFF",
] as const;

// Spec version emitted by the XML serializer. Matches the default
// `spec_version` in pyoutline config. Cuebot servers that don't
// understand newer features fall back gracefully on older specs.
export const SPEC_VERSION = "1.13";

// localStorage key for the in-progress draft so an accidental refresh
// doesn't wipe a 10-layer setup. Cleared on successful submit.
export const DRAFT_STORAGE_KEY = "cueweb.cuesubmit.draft.v1";
