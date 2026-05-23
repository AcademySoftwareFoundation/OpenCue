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
import { useRouter } from "next/navigation";
import { useSession } from "next-auth/react";
import { Controller, useFieldArray, useForm, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";

import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { Switch } from "@/components/ui/switch";
import { useCuebotFacility } from "@/app/utils/use_cuebot_facility";
import { handleError, toastSuccess } from "@/app/utils/notify_utils";
import { toast } from "react-toastify";

import {
  DEFAULT_LIMITS,
  DEFAULT_SERVICES,
  DEPENDENCY_TYPES,
  DRAFT_STORAGE_KEY,
  JOB_TYPES,
  type JobType,
} from "./lib/constants";
import { buildLayerCommand } from "./lib/commands";
import { fetchShows, type ShowOption } from "./lib/getShows";
import {
  submissionSchema,
  type LayerInput,
  type Submission,
} from "./lib/schemas";

import { Field } from "./components/field";
import { HelpPopover } from "./components/help_popover";
import {
  HISTORY_CHANGED_EVENT,
  HistoryInput,
} from "./components/history_input";
import { LayersTable } from "./components/layers_table";
import { SectionHeader } from "./components/section_header";
import { rememberSubmission } from "./lib/history";
import {
  BlenderOptions,
  MayaOptions,
  NukeOptions,
  ShellOptions,
} from "./components/type_options";

function makeBlankLayer(index: number): LayerInput {
  return {
    name: index === 0 ? "" : `layer_${index + 1}`,
    frameSpec: "",
    chunkSize: 1,
    jobType: "Shell" as JobType,
    services: [],
    limits: [],
    overrideCores: false,
    cores: 0,
    memory: "256m",
    dependencyType: "",
    shell: { command: "" },
    maya: { mayaFile: "", camera: "" },
    nuke: { nukeFile: "", writeNodes: "" },
    blender: { blenderFile: "", outputPath: "", outputFormat: "" },
  };
}

export default function CueSubmitPage() {
  const router = useRouter();
  const { data: session } = useSession();
  const { facilities, facility } = useCuebotFacility();
  const [shows, setShows] = React.useState<ShowOption[]>([]);
  const [showsLoading, setShowsLoading] = React.useState(true);
  const [selectedIndex, setSelectedIndex] = React.useState(0);
  const [submitting, setSubmitting] = React.useState(false);
  // Username override toggle. When a signed-in user populates the
  // Username field, it stays read-only until the user explicitly ticks
  // "Edit". Sandbox mode (no signed-in user) skips the lock entirely.
  const [editUsername, setEditUsername] = React.useState(false);

  const username = React.useMemo(() => {
    if (session?.user?.email) return session.user.email.split("@")[0];
    if (session?.user?.name) return String(session.user.name);
    return "";
  }, [session?.user]);

  const form = useForm<Submission>({
    resolver: zodResolver(submissionSchema),
    defaultValues: {
      job: { name: "", show: "", shot: "", facility: facility || "", user: "" },
      layers: [makeBlankLayer(0)],
    },
    mode: "onBlur",
  });

  const {
    control,
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors },
    reset,
  } = form;
  const { fields, append, remove, move } = useFieldArray({
    control,
    name: "layers",
  });

  // useWatch instead of watch("layers") because RHF can mutate nested
  // field values in place when re-rendering uncontrolled inputs (the
  // outer `layers` reference stays stable across typing), which makes
  // useMemo skip re-running and freezes the Final command preview.
  // useWatch returns a fresh object snapshot on every form change.
  const layers = useWatch({
    control,
    name: "layers",
    defaultValue: form.getValues("layers"),
  }) as LayerInput[];
  const currentLayer = layers[selectedIndex] ?? layers[0];

  // Load shows for the dropdown and seed user / facility once the
  // session / facility hook resolve. We deliberately re-set these
  // through setValue (not in defaultValues) so re-rendering while the
  // session is still loading doesn't reset whatever the user typed.
  React.useEffect(() => {
    let cancelled = false;
    setShowsLoading(true);
    fetchShows()
      .then((data) => {
        if (cancelled) return;
        setShows(data);
        if (data.length > 0) {
          // Use functional update via getValues so we don't overwrite a
          // show the user already picked.
          const current = form.getValues("job.show");
          if (!current) setValue("job.show", data[0].name);
        }
      })
      .finally(() => {
        if (!cancelled) setShowsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [form, setValue]);

  React.useEffect(() => {
    if (username) setValue("job.user", username, { shouldValidate: false });
  }, [username, setValue]);

  React.useEffect(() => {
    if (facility && !form.getValues("job.facility")) {
      setValue("job.facility", facility);
    }
  }, [facility, form, setValue]);

  // Draft persistence: save the form on every change to localStorage
  // and restore on mount so an accidental refresh doesn't wipe a
  // multi-layer setup. Cleared on successful submit.
  React.useEffect(() => {
    if (typeof window === "undefined") return;
    try {
      const raw = localStorage.getItem(DRAFT_STORAGE_KEY);
      if (!raw) return;
      const parsed = JSON.parse(raw);
      if (parsed && typeof parsed === "object") {
        reset(parsed);
      }
    } catch {
      // ignore corrupt draft
    }
  }, [reset]);

  React.useEffect(() => {
    if (typeof window === "undefined") return;
    const sub = form.watch((values) => {
      try {
        localStorage.setItem(DRAFT_STORAGE_KEY, JSON.stringify(values));
      } catch {
        // private mode / quota - ignore
      }
    });
    return () => sub.unsubscribe();
  }, [form]);

  // Final-command preview. Build silently so missing fields show a
  // visible "!! missing X !!" instead of throwing while the user types.
  const finalCommand = React.useMemo(() => {
    try {
      return buildLayerCommand(currentLayer, { silent: true });
    } catch {
      return "";
    }
  }, [currentLayer]);

  const overrideCores = watch(`layers.${selectedIndex}.overrideCores`);
  const jobType = watch(`layers.${selectedIndex}.jobType`);

  function handleAddLayer() {
    append(makeBlankLayer(fields.length));
    setSelectedIndex(fields.length); // post-append the new index is fields.length
  }
  function handleRemoveLayer() {
    if (fields.length <= 1) return;
    const removeIdx = selectedIndex;
    remove(removeIdx);
    setSelectedIndex((prev) => Math.max(0, prev - 1));
  }
  function handleMoveUp() {
    if (selectedIndex <= 0) return;
    move(selectedIndex, selectedIndex - 1);
    setSelectedIndex((i) => i - 1);
  }
  function handleMoveDown() {
    if (selectedIndex >= fields.length - 1) return;
    move(selectedIndex, selectedIndex + 1);
    setSelectedIndex((i) => i + 1);
  }
  function handleCancel() {
    try {
      localStorage.removeItem(DRAFT_STORAGE_KEY);
    } catch {
      /* ignore */
    }
    router.push("/");
  }

  // Clear everything and start fresh. The page auto-saves the form to
  // localStorage on every keystroke and restores on mount (so a tab
  // refresh doesn't wipe a multi-layer setup), but that means the
  // form always boots showing the last submission's leftovers. Reset
  // gives the user an explicit way to get a blank canvas without
  // clearing the autocomplete history they've built up.
  const [resetDialogOpen, setResetDialogOpen] = React.useState(false);
  function performReset() {
    try {
      localStorage.removeItem(DRAFT_STORAGE_KEY);
    } catch {
      /* ignore */
    }
    reset({
      job: {
        name: "",
        show: shows[0]?.name ?? "",
        shot: "",
        facility: facility || "",
        user: username,
      },
      layers: [makeBlankLayer(0)],
    });
    setSelectedIndex(0);
  }

  async function onSubmit(values: Submission) {
    setSubmitting(true);
    try {
      const res = await fetch("/api/job/submit", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(values),
      });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) {
        // handleError only fires a toast when an explicit message is
        // passed - so surface the cuebot error inline here instead of
        // burying it in a server-side log nobody will see.
        const message = body?.error
          ? `Job submission failed: ${body.error}`
          : "Job submission failed.";
        toast.error(message, { autoClose: 8000 });
        handleError(new Error(message), message);
        return;
      }
      toastSuccess(
        `Submitted "${values.job.name}" - ${values.layers.length} layer(s)`,
      );
      // Cache the values we just submitted so they autocomplete next
      // time. cuesubmit Python does the same on its on-disk cache.
      rememberSubmission({
        jobName: values.job.name,
        shot: values.job.shot,
        layers: values.layers,
      });
      window.dispatchEvent(new Event(HISTORY_CHANGED_EVENT));
      try {
        localStorage.removeItem(DRAFT_STORAGE_KEY);
      } catch {
        /* ignore */
      }
      const jobName = body?.jobs?.[0]?.data?.name ?? body?.jobs?.[0]?.name ?? values.job.name;
      router.push(`/jobs/${encodeURIComponent(jobName)}`);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Job submission failed.";
      toast.error(message, { autoClose: 8000 });
      handleError(err, message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="container mx-auto py-6 max-w-5xl">
      <header className="mb-4">
        <h1 className="text-2xl font-semibold">CueSubmit</h1>
        <p className="text-sm text-foreground/70">
          Submit a job to OpenCue. Mirrors the standalone CueSubmit
          CLI tool - configure one or more layers, preview the final
          command, then submit.
        </p>
      </header>

      <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-4">
        <SectionHeader label="Job Info" />
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <Field
            label="Job Name"
            required
            invalid={!!errors.job?.name}
            hint={errors.job?.name?.message}
            className="sm:col-span-2"
            htmlFor="job-name"
          >
            <HistoryInput
              id="job-name"
              type="text"
              historyField="jobName"
              autoComplete="off"
              className="rounded-md border border-input bg-background px-3 py-2 text-sm"
              {...register("job.name")}
            />
          </Field>
          <Field
            label="Show"
            required
            invalid={!!errors.job?.show}
            hint={errors.job?.show?.message}
          >
            <Controller
              control={control}
              name="job.show"
              render={({ field }) => (
                <select
                  {...field}
                  className="rounded-md border border-input bg-background px-3 py-2 text-sm"
                  disabled={showsLoading}
                >
                  {shows.length === 0 && (
                    <option value="">
                      {showsLoading ? "Loading..." : "No shows available"}
                    </option>
                  )}
                  {shows.map((s) => (
                    <option key={s.id || s.name} value={s.name}>
                      {s.name}
                    </option>
                  ))}
                </select>
              )}
            />
          </Field>
          <Field
            label="Shot"
            required
            invalid={!!errors.job?.shot}
            hint={errors.job?.shot?.message}
          >
            <HistoryInput
              type="text"
              historyField="shot"
              autoComplete="off"
              className="rounded-md border border-input bg-background px-3 py-2 text-sm"
              {...register("job.shot")}
            />
          </Field>
          <Field label="Facility">
            <Controller
              control={control}
              name="job.facility"
              render={({ field }) => (
                <select
                  {...field}
                  value={field.value || ""}
                  className="rounded-md border border-input bg-background px-3 py-2 text-sm"
                >
                  <option value="">[Default]</option>
                  {facilities.map((f) => (
                    <option key={f} value={f}>
                      {f}
                    </option>
                  ))}
                </select>
              )}
            />
          </Field>
          <Field label="Username" required invalid={!!errors.job?.user}>
            <div className="flex items-center gap-2">
              <input
                type="text"
                readOnly={!!username && !editUsername}
                aria-readonly={!!username && !editUsername}
                className={
                  "flex-1 rounded-md border border-input px-3 py-2 text-sm " +
                  (!!username && !editUsername
                    ? "bg-foreground/[0.04] cursor-not-allowed"
                    : "bg-background")
                }
                {...register("job.user")}
              />
              {/* Only offer the override toggle when a signed-in user
                  populated the field. In sandbox mode (no session) the
                  field is always editable, no toggle needed. */}
              {!!username && (
                <label className="inline-flex items-center gap-1.5 text-xs text-foreground/70 whitespace-nowrap">
                  <input
                    type="checkbox"
                    checked={editUsername}
                    onChange={(e) => {
                      const enabled = e.target.checked;
                      setEditUsername(enabled);
                      // Unticking snaps the value back to the
                      // signed-in user - matches the "Override" toggle
                      // pattern used elsewhere in the app.
                      if (!enabled) {
                        setValue("job.user", username, {
                          shouldValidate: false,
                        });
                      }
                    }}
                  />
                  Edit
                </label>
              )}
            </div>
          </Field>
        </div>

        <SectionHeader label="Layer Info" />
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <Field
            label="Layer Name"
            required
            className="sm:col-span-2"
            invalid={!!errors.layers?.[selectedIndex]?.name}
            hint={errors.layers?.[selectedIndex]?.name?.message}
          >
            <HistoryInput
              type="text"
              historyField="layerName"
              autoComplete="off"
              className="rounded-md border border-input bg-background px-3 py-2 text-sm"
              {...register(`layers.${selectedIndex}.name`)}
            />
          </Field>
          <Field label="Dependency Type">
            <Controller
              control={control}
              name={`layers.${selectedIndex}.dependencyType`}
              render={({ field }) => (
                <select
                  {...field}
                  className="rounded-md border border-input bg-background px-3 py-2 text-sm"
                >
                  {DEPENDENCY_TYPES.map((dt) => (
                    <option key={dt || "_none_"} value={dt}>
                      {dt || "(none)"}
                    </option>
                  ))}
                </select>
              )}
            />
          </Field>

          <Field
            label="Frame Spec"
            required
            invalid={!!errors.layers?.[selectedIndex]?.frameSpec}
            hint={errors.layers?.[selectedIndex]?.frameSpec?.message}
            className="sm:col-span-2"
          >
            <div className="flex items-start gap-2">
              <input
                type="text"
                className="flex-1 rounded-md border border-input bg-background px-3 py-2 text-sm font-mono"
                placeholder="1-100"
                {...register(`layers.${selectedIndex}.frameSpec`)}
              />
              <HelpPopover kind="frame-spec" />
            </div>
          </Field>
          <Field label="Chunk Size">
            <input
              type="number"
              min={1}
              className="rounded-md border border-input bg-background px-3 py-2 text-sm"
              {...register(`layers.${selectedIndex}.chunkSize`, {
                valueAsNumber: true,
              })}
            />
          </Field>

          <Field
            label="Memory"
            invalid={!!errors.layers?.[selectedIndex]?.memory}
            hint={
              errors.layers?.[selectedIndex]?.memory?.message ||
              "Per-frame request, e.g. 256m, 1g. Empty = service default."
            }
            className="sm:col-span-3"
          >
            <input
              type="text"
              className="rounded-md border border-input bg-background px-3 py-2 text-sm w-40 font-mono"
              placeholder="256m"
              {...register(`layers.${selectedIndex}.memory`)}
            />
          </Field>

          <Field label="Job Type">
            <Controller
              control={control}
              name={`layers.${selectedIndex}.jobType`}
              render={({ field }) => (
                <select
                  {...field}
                  className="rounded-md border border-input bg-background px-3 py-2 text-sm"
                >
                  {JOB_TYPES.map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </select>
              )}
            />
          </Field>
          <Field label="Services">
            <Controller
              control={control}
              name={`layers.${selectedIndex}.services`}
              render={({ field }) => (
                <select
                  value={field.value?.[0] ?? ""}
                  onChange={(e) =>
                    field.onChange(e.target.value ? [e.target.value] : [])
                  }
                  className="rounded-md border border-input bg-background px-3 py-2 text-sm"
                >
                  <option value="">[None]</option>
                  {DEFAULT_SERVICES.map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
                </select>
              )}
            />
          </Field>
          <Field label="Limits">
            <Controller
              control={control}
              name={`layers.${selectedIndex}.limits`}
              render={({ field }) => (
                <select
                  value={field.value?.[0] ?? ""}
                  onChange={(e) =>
                    field.onChange(e.target.value ? [e.target.value] : [])
                  }
                  className="rounded-md border border-input bg-background px-3 py-2 text-sm"
                  disabled={DEFAULT_LIMITS.length === 0}
                >
                  <option value="">[None]</option>
                  {DEFAULT_LIMITS.map((l) => (
                    <option key={l} value={l}>
                      {l}
                    </option>
                  ))}
                </select>
              )}
            />
          </Field>

          <div className="sm:col-span-3 flex items-center gap-3">
            <Controller
              control={control}
              name={`layers.${selectedIndex}.overrideCores`}
              render={({ field }) => (
                <Switch
                  checked={!!field.value}
                  onCheckedChange={(v) => field.onChange(v)}
                  aria-label="Override service core count"
                />
              )}
            />
            <Field label="Override Cores" htmlFor="cores-input" className="flex-row items-center gap-2">
              <input
                id="cores-input"
                type="number"
                min={0}
                step={0.5}
                disabled={!overrideCores}
                className="w-24 rounded-md border border-input bg-background px-3 py-2 text-sm disabled:opacity-50"
                {...register(`layers.${selectedIndex}.cores`, {
                  valueAsNumber: true,
                })}
              />
            </Field>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-3 mt-2">
          {jobType === "Shell" && (
            <ShellOptions
              pathPrefix={`layers.${selectedIndex}.`}
              control={control}
              register={register}
              errors={errors.layers?.[selectedIndex]}
            />
          )}
          {jobType === "Maya" && (
            <MayaOptions
              pathPrefix={`layers.${selectedIndex}.`}
              control={control}
              register={register}
              errors={errors.layers?.[selectedIndex]}
            />
          )}
          {jobType === "Nuke" && (
            <NukeOptions
              pathPrefix={`layers.${selectedIndex}.`}
              control={control}
              register={register}
              errors={errors.layers?.[selectedIndex]}
            />
          )}
          {jobType === "Blender" && (
            <BlenderOptions
              pathPrefix={`layers.${selectedIndex}.`}
              control={control}
              register={register}
              errors={errors.layers?.[selectedIndex]}
            />
          )}
        </div>

        <Field label="Final command" className="mt-2">
          <input
            type="text"
            readOnly
            value={finalCommand}
            className="rounded-md border border-input bg-foreground/[0.04] px-3 py-2 text-sm font-mono"
          />
        </Field>

        <SectionHeader label="Submission Details" />
        <LayersTable
          layers={layers}
          selectedIndex={selectedIndex}
          onSelect={setSelectedIndex}
          onAdd={handleAddLayer}
          onRemove={handleRemoveLayer}
          onMoveUp={handleMoveUp}
          onMoveDown={handleMoveDown}
          disabled={submitting}
        />

        <div className="flex justify-end gap-2 pt-4">
          <Button
            type="button"
            variant="outline"
            onClick={handleCancel}
            disabled={submitting}
          >
            Cancel
          </Button>
          <Button
            type="button"
            variant="outline"
            onClick={() => setResetDialogOpen(true)}
            disabled={submitting}
            title="Clear every field and start with a blank form"
          >
            Reset
          </Button>
          <Button type="submit" disabled={submitting}>
            {submitting ? "Submitting..." : "Submit"}
          </Button>
        </div>
      </form>

      <ConfirmDialog
        open={resetDialogOpen}
        onOpenChange={setResetDialogOpen}
        title="Reset the form?"
        description="All Job Info and Layer Info fields will be cleared. Your autocomplete history is kept."
        confirmLabel="Reset"
        variant="destructive"
        onConfirm={performReset}
      />
    </div>
  );
}
