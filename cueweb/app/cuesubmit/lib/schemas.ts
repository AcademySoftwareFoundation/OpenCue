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

import { z } from "zod";

import { JOB_TYPES, DEPENDENCY_TYPES } from "./constants";
import { isValidFrameSpec } from "./frame_spec";

// CueGUI / cuesubmit accept the same identifier rules across show,
// shot, job name, layer name: letters, numbers, dot, dash, underscore,
// and basic whitespace. We reject embedded spaces in job/layer names
// because cuebot uses the name directly in the log path.
const NAME_RE = /^[A-Za-z0-9._-]+$/;

export const jobInfoSchema = z.object({
  name: z
    .string()
    .min(1, "Job Name is required.")
    .regex(NAME_RE, "Letters, numbers, '.', '-', '_' only."),
  show: z.string().min(1, "Show is required."),
  shot: z
    .string()
    .min(1, "Shot is required.")
    .regex(NAME_RE, "Letters, numbers, '.', '-', '_' only."),
  facility: z.string().optional().default(""),
  user: z.string().min(1, "User Name is required."),
});

export type JobInfo = z.infer<typeof jobInfoSchema>;

// Per-type option shapes. Keeping each as its own object instead of a
// discriminated union so react-hook-form can drive a single form and
// only the relevant slice is read on submit. Each is `partial` here so
// the layer form can be edited freely; the per-type builder asserts
// the fields it actually needs.

export const shellOptionsSchema = z.object({
  command: z.string().default(""),
});

export const mayaOptionsSchema = z.object({
  mayaFile: z.string().default(""),
  camera: z.string().default(""),
});

export const nukeOptionsSchema = z.object({
  nukeFile: z.string().default(""),
  writeNodes: z.string().default(""),
});

export const blenderOptionsSchema = z.object({
  blenderFile: z.string().default(""),
  outputPath: z.string().default(""),
  outputFormat: z.string().default(""),
});

// Memory accepts a number (KiB) or a unit-suffixed string like "256m",
// "3g", "3.2G". cuebot accepts both forms in <memory>. We keep it as a
// string so the user can type whichever is most natural and so the
// spec emits exactly what was typed (cuebot's parser handles the
// conversion). Empty = omit the element and inherit the service's
// minimum.
const MEMORY_RE = /^(\d+(?:\.\d+)?)(k|kb|m|mb|g|gb)?$/i;

export const layerSchema = z.object({
  name: z
    .string()
    .min(1, "Layer Name is required.")
    .regex(NAME_RE, "Letters, numbers, '.', '-', '_' only."),
  frameSpec: z
    .string()
    .min(1, "Frame Spec is required.")
    .refine(isValidFrameSpec, {
      message: "Use forms like '1-10', '1-100x2', or '1,3,5'.",
    }),
  chunkSize: z.coerce.number().int().min(1).default(1),
  jobType: z.enum(JOB_TYPES),
  services: z.array(z.string()).default([]),
  limits: z.array(z.string()).default([]),
  overrideCores: z.boolean().default(false),
  cores: z.coerce.number().min(0).default(0),
  // Memory request per frame. Empty = inherit service min. Default
  // "256m" mirrors what production cuesubmit users typically pass on
  // the Python side; without it the default service's 3.2 GB minimum
  // keeps trivial jobs stuck in WAITING on small RQDs.
  memory: z
    .string()
    .default("256m")
    .refine((v) => v === "" || MEMORY_RE.test(v), {
      message: "Use a number plus optional unit (e.g. 256m, 1g, 3.2G).",
    }),
  dependencyType: z.enum(DEPENDENCY_TYPES).default(""),
  shell: shellOptionsSchema.default({ command: "" }),
  maya: mayaOptionsSchema.default({ mayaFile: "", camera: "" }),
  nuke: nukeOptionsSchema.default({ nukeFile: "", writeNodes: "" }),
  blender: blenderOptionsSchema.default({
    blenderFile: "",
    outputPath: "",
    outputFormat: "",
  }),
});

export type LayerInput = z.infer<typeof layerSchema>;

export const submissionSchema = z.object({
  job: jobInfoSchema,
  layers: z
    .array(layerSchema)
    .min(1, "At least one layer is required."),
});

export type Submission = z.infer<typeof submissionSchema>;
