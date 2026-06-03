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

// Per-type command builders. Direct port of cuesubmit/Submission.py's
// buildShellCmd / buildMayaCmd / buildNukeCmd / buildBlenderCmd. Live
// preview in the UI calls these synchronously; the submit endpoint
// calls the exact same functions to build what actually gets sent to
// cuebot.

import {
  BLENDER_RENDER_CMD,
  FRAME_END_TOKEN,
  FRAME_START_TOKEN,
  FRAME_TOKEN,
  MAYA_RENDER_CMD,
  NUKE_RENDER_CMD,
} from "./constants";
import { isSimpleRange } from "./frame_spec";
import type { LayerInput } from "./schemas";

export function buildShellCommand(layer: LayerInput): string {
  return layer.shell.command.trim();
}

export function buildMayaCommand(layer: LayerInput): string {
  const { mayaFile, camera } = layer.maya;
  // Mirrors buildMayaCmd in cuesubmit/Submission.py. The frame range
  // tokens are substituted by cuebot at dispatch.
  let cmd = `${MAYA_RENDER_CMD} -r file -s ${FRAME_START_TOKEN} -e ${FRAME_END_TOKEN}`;
  if (camera) cmd += ` -cam ${camera}`;
  if (mayaFile) cmd += ` ${mayaFile}`;
  return cmd;
}

export function buildNukeCommand(layer: LayerInput): string {
  const { nukeFile, writeNodes } = layer.nuke;
  let cmd = `${NUKE_RENDER_CMD} -F ${FRAME_TOKEN} `;
  if (writeNodes) cmd += `-X ${writeNodes} `;
  if (nukeFile) cmd += `-x ${nukeFile}`;
  return cmd.trimEnd();
}

export function buildBlenderCommand(layer: LayerInput): string {
  const { blenderFile, outputPath, outputFormat } = layer.blender;
  let cmd = `${BLENDER_RENDER_CMD} -b -noaudio`;
  if (blenderFile) cmd += ` ${blenderFile}`;
  if (outputPath) cmd += ` -o ${outputPath}`;
  if (outputFormat) cmd += ` -F ${outputFormat}`;
  // For a simple "start-end" range, Blender renders the whole range in
  // one process via -a; otherwise cuebot dispatches one frame per
  // chunk and we use the per-frame -f token instead.
  if (isSimpleRange(layer.frameSpec)) {
    cmd += ` -s ${FRAME_START_TOKEN} -e ${FRAME_END_TOKEN} -a`;
  } else {
    cmd += ` -f ${FRAME_TOKEN}`;
  }
  return cmd;
}

/**
 * Dispatcher mirroring buildLayerCommand in Submission.py. `silent`
 * mode (used by the UI preview) substitutes a "!! missing X !!"
 * sentinel instead of throwing so the user can see what they still
 * need to fill in. Strict mode (used by the submit endpoint) throws.
 */
export function buildLayerCommand(
  layer: LayerInput,
  opts: { silent: boolean } = { silent: false },
): string {
  switch (layer.jobType) {
    case "Shell": {
      // Mirrors cuesubmit Python: silent mode returns whatever is in
      // the Command To Run box verbatim (empty when empty). Only the
      // strict path enforces non-empty since the submit endpoint
      // cannot send an empty <cmd> to cuebot.
      const cmd = layer.shell.command.trim();
      if (!cmd && !opts.silent) {
        throw new Error(`Layer '${layer.name}' is missing a command.`);
      }
      return cmd;
    }
    case "Maya":
      if (!layer.maya.mayaFile && !opts.silent) {
        throw new Error(`Layer '${layer.name}' is missing a Maya file.`);
      }
      return buildMayaCommand(layer);
    case "Nuke":
      if (!layer.nuke.nukeFile && !opts.silent) {
        throw new Error(`Layer '${layer.name}' is missing a Nuke file.`);
      }
      return buildNukeCommand(layer);
    case "Blender":
      if (!layer.blender.blenderFile && !opts.silent) {
        throw new Error(`Layer '${layer.name}' is missing a Blender file.`);
      }
      return buildBlenderCommand(layer);
    default:
      if (opts.silent) return `!! unsupported job type ${layer.jobType} !!`;
      throw new Error(`Unsupported job type: ${layer.jobType}`);
  }
}
