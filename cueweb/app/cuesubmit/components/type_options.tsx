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

"use client";

import * as React from "react";
import { Controller } from "react-hook-form";

import { BLENDER_FORMATS } from "../lib/constants";

import { Field } from "./field";
import { HelpPopover } from "./help_popover";

// Per-job-type "<X> options" panel. Visible only when the currently
// edited layer's jobType matches. The form keeps values for every
// type at all times so a user can flip between Maya / Nuke / Blender
// while iterating without losing previously-typed fields.
//
// `pathPrefix` is the parent form's path to this layer (e.g.
// `layers.3.`). All field names below are appended to it. The form
// generic is wider than LayerInput, so we accept hook-form callbacks
// as `any` rather than fight TypeScript on path-string types.

type Props = {
  pathPrefix: string;
  control: any;
  register: any;
  errors: any;
};

export function ShellOptions({ pathPrefix, register, errors }: Props) {
  return (
    <Panel title="Shell options">
      <Field
        label="Command To Run"
        required
        invalid={!!errors?.shell?.command}
        htmlFor="shell-command"
        hint={errors?.shell?.command?.message}
      >
        <div className="flex items-start gap-2">
          <textarea
            id="shell-command"
            rows={4}
            className="flex-1 rounded-md border border-input bg-background px-3 py-2 text-sm font-mono"
            placeholder='echo "frame ${FRAME}"'
            {...register(`${pathPrefix}shell.command`)}
          />
          <HelpPopover kind="command" />
        </div>
      </Field>
    </Panel>
  );
}

export function MayaOptions({ pathPrefix, register, errors }: Props) {
  return (
    <Panel title="Maya options">
      <Field
        label="Maya File"
        required
        invalid={!!errors?.maya?.mayaFile}
        hint={errors?.maya?.mayaFile?.message}
      >
        <input
          type="text"
          className="rounded-md border border-input bg-background px-3 py-2 text-sm"
          placeholder="/path/to/scene.ma"
          {...register(`${pathPrefix}maya.mayaFile`)}
        />
      </Field>
      <Field label="Camera (optional)">
        <input
          type="text"
          className="rounded-md border border-input bg-background px-3 py-2 text-sm"
          placeholder="renderCam"
          {...register(`${pathPrefix}maya.camera`)}
        />
      </Field>
    </Panel>
  );
}

export function NukeOptions({ pathPrefix, register, errors }: Props) {
  return (
    <Panel title="Nuke options">
      <Field
        label="Nuke File"
        required
        invalid={!!errors?.nuke?.nukeFile}
        hint={errors?.nuke?.nukeFile?.message}
      >
        <input
          type="text"
          className="rounded-md border border-input bg-background px-3 py-2 text-sm"
          placeholder="/path/to/script.nk"
          {...register(`${pathPrefix}nuke.nukeFile`)}
        />
      </Field>
      <Field label="Write Nodes (optional, comma-separated)">
        <input
          type="text"
          className="rounded-md border border-input bg-background px-3 py-2 text-sm"
          placeholder="Write1,Write2"
          {...register(`${pathPrefix}nuke.writeNodes`)}
        />
      </Field>
    </Panel>
  );
}

export function BlenderOptions({
  pathPrefix,
  control,
  register,
  errors,
}: Props) {
  return (
    <Panel title="Blender options">
      <Field
        label="Blender File"
        required
        invalid={!!errors?.blender?.blenderFile}
        hint={errors?.blender?.blenderFile?.message}
      >
        <input
          type="text"
          className="rounded-md border border-input bg-background px-3 py-2 text-sm"
          placeholder="/path/to/scene.blend"
          {...register(`${pathPrefix}blender.blenderFile`)}
        />
      </Field>
      <Field label="Output Path (optional)">
        <input
          type="text"
          className="rounded-md border border-input bg-background px-3 py-2 text-sm"
          placeholder="/path/to/output/####"
          {...register(`${pathPrefix}blender.outputPath`)}
        />
      </Field>
      <Field label="Output Format (optional)">
        <Controller
          control={control}
          name={`${pathPrefix}blender.outputFormat`}
          render={({ field }) => (
            <select
              {...field}
              className="rounded-md border border-input bg-background px-3 py-2 text-sm"
            >
              {BLENDER_FORMATS.map((f) => (
                <option key={f || "_none_"} value={f}>
                  {f || "(leave unspecified)"}
                </option>
              ))}
            </select>
          )}
        />
      </Field>
    </Panel>
  );
}

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <fieldset className="rounded-md border border-foreground/20 p-3">
      <legend className="px-1 text-xs text-foreground/60">{title}</legend>
      <div className="grid grid-cols-1 gap-3">{children}</div>
    </fieldset>
  );
}
