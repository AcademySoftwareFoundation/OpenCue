"use client";

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

import * as React from "react";

import type { Service } from "@/app/utils/get_utils";
import { createService, updateService } from "@/app/utils/action_utils";
import { toastSuccess, toastWarning } from "@/app/utils/notify_utils";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { Input } from "@/components/ui/input";

/**
 * Facility Service Defaults edit form (CueGUI ServiceForm parity). The right
 * pane of the Facility Service Defaults page: an editable form for one service
 * template. Memory fields are MB in the UI but KB in the proto (x1024), and
 * threads are stored as cores*100 (100 = 1 thread, shown directly). Save shows
 * a facility-wide confirmation, then calls Create (new) or Update (existing).
 *
 * The parent remounts this via a `key` when the selected service changes, so
 * state initializes straight from props.
 */

// Predefined tag order matches CueGUI's CheckBoxSelectionMatrix (row-major,
// two columns): general/desktop, playblast/util, preprocess/wan, cuda/splathw,
// naiad/massive.
const PREDEFINED_TAGS = [
  "general",
  "desktop",
  "playblast",
  "util",
  "preprocess",
  "wan",
  "cuda",
  "splathw",
  "naiad",
  "massive",
];

const toMb = (kb: number | string | undefined) => Math.round(Number(kb ?? 0) / 1024);
const parseCustomTags = (text: string) => text.split(/[\s,|]+/).filter(Boolean);

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-[14rem_1fr] items-center gap-3">
      <label className="text-sm text-muted-foreground">{label}</label>
      {children}
    </div>
  );
}

export function ServiceDefaultsForm({
  service,
  onSaved,
}: {
  // null => creating a new service.
  service: Service | null;
  onSaved: (name: string) => void;
}) {
  const isNew = service === null;

  const initAllPredefined = !service || service.tags.every((t) => PREDEFINED_TAGS.includes(t));

  const [name, setName] = React.useState(service?.name ?? "");
  const [threadable, setThreadable] = React.useState(service?.threadable ?? false);
  const [minThreads, setMinThreads] = React.useState(String(service?.minCores ?? 100));
  const [maxThreads, setMaxThreads] = React.useState(String(service?.maxCores ?? 100));
  const [minMemoryMb, setMinMemoryMb] = React.useState(String(service ? toMb(service.minMemory) : 3276));
  const [minGpuMemoryMb, setMinGpuMemoryMb] = React.useState(String(service ? toMb(service.minGpuMemory) : 0));
  const [timeout, setTimeoutMin] = React.useState(String(service?.timeout ?? 0));
  const [timeoutLlu, setTimeoutLlu] = React.useState(String(service?.timeoutLlu ?? 0));
  const [oomIncreaseMb, setOomIncreaseMb] = React.useState(String(service ? toMb(service.minMemoryIncrease) : 2048));

  const [useCustomTags, setUseCustomTags] = React.useState(!initAllPredefined);
  const [selectedTags, setSelectedTags] = React.useState<Set<string>>(
    new Set(initAllPredefined ? service?.tags ?? ["general"] : []),
  );
  const [customTags, setCustomTags] = React.useState(initAllPredefined ? "" : (service?.tags ?? []).join(" "));

  const [confirmOpen, setConfirmOpen] = React.useState(false);

  function toggleTag(tag: string, checked: boolean) {
    setSelectedTags((prev) => {
      const next = new Set(prev);
      if (checked) next.add(tag);
      else next.delete(tag);
      return next;
    });
  }

  function resolveTags(): string[] {
    return useCustomTags ? parseCustomTags(customTags) : PREDEFINED_TAGS.filter((t) => selectedTags.has(t));
  }

  // Returns an error message, or null when the form is valid.
  function validate(): string | null {
    const n = name.trim();
    if (n.length < 3) return "Service name must be at least 3 characters.";
    if (!/^[a-zA-Z0-9|/_-]+$/.test(n)) return "Service name may only contain letters, numbers, and | / - _";

    const numericFields: [string, string][] = [
      ["Min Threads", minThreads],
      ["Max Threads", maxThreads],
      ["Min Memory MB", minMemoryMb],
      ["Min Gpu Memory MB", minGpuMemoryMb],
      ["Timeout", timeout],
      ["Timeout LLU", timeoutLlu],
      ["OOM Increase MB", oomIncreaseMb],
    ];
    for (const [fieldLabel, value] of numericFields) {
      const x = Number(value);
      if (value.trim() === "" || !Number.isFinite(x) || x < 0) {
        return `${fieldLabel} must be a non-negative number.`;
      }
    }
    if (Number(maxThreads) > 0 && Number(minThreads) > Number(maxThreads)) {
      return "Min Threads cannot exceed Max Threads.";
    }
    if (Number(oomIncreaseMb) <= 0) {
      return "OOM Increase must be greater than 0 MB.";
    }
    if (useCustomTags) {
      const tags = parseCustomTags(customTags);
      if (tags.length === 0) return "Enter at least one custom tag.";
      if (tags.some((t) => !/^[a-zA-Z0-9_-]+$/.test(t))) {
        return "Custom tags may only contain letters, numbers, _ and -.";
      }
    } else if (selectedTags.size === 0) {
      return "Select at least one tag.";
    }
    return null;
  }

  function handleSaveClick() {
    const err = validate();
    if (err) {
      toastWarning(err);
      return;
    }
    setConfirmOpen(true);
  }

  async function handleConfirm() {
    const payload: Service = {
      id: service?.id ?? "",
      name: name.trim(),
      threadable,
      minCores: Number(minThreads),
      maxCores: Number(maxThreads),
      minMemory: Number(minMemoryMb) * 1024,
      minGpuMemory: Number(minGpuMemoryMb) * 1024,
      tags: resolveTags(),
      timeout: Number(timeout),
      timeoutLlu: Number(timeoutLlu),
      minGpus: service?.minGpus ?? 0,
      maxGpus: service?.maxGpus ?? 0,
      minMemoryIncrease: Number(oomIncreaseMb) * 1024,
    };
    const ok = isNew ? await createService(payload) : await updateService(payload);
    if (ok) {
      toastSuccess(isNew ? `Created service ${payload.name}` : `Saved service ${payload.name}`);
      onSaved(payload.name);
    }
  }

  return (
    <div className="space-y-3">
      <Field label="Name:">
        <Input value={name} onChange={(e) => setName(e.target.value)} aria-label="Name" />
      </Field>
      <Field label="Threadable:">
        <Checkbox
          checked={threadable}
          onCheckedChange={(c) => setThreadable(!!c)}
          aria-label="Threadable"
        />
      </Field>
      <Field label="Min Threads (100 = 1 thread):">
        <Input type="number" min={0} value={minThreads} onChange={(e) => setMinThreads(e.target.value)} aria-label="Min Threads" />
      </Field>
      <Field label="Max Threads (100 = 1 thread):">
        <Input type="number" min={0} value={maxThreads} onChange={(e) => setMaxThreads(e.target.value)} aria-label="Max Threads" />
      </Field>
      <Field label="Min Memory MB:">
        <Input type="number" min={0} value={minMemoryMb} onChange={(e) => setMinMemoryMb(e.target.value)} aria-label="Min Memory MB" />
      </Field>
      <Field label="Min Gpu Memory MB:">
        <Input type="number" min={0} value={minGpuMemoryMb} onChange={(e) => setMinGpuMemoryMb(e.target.value)} aria-label="Min Gpu Memory MB" />
      </Field>
      <Field label="Timeout (in minutes):">
        <Input type="number" min={0} value={timeout} onChange={(e) => setTimeoutMin(e.target.value)} aria-label="Timeout" />
      </Field>
      <Field label="Timeout LLU (in minutes):">
        <Input type="number" min={0} value={timeoutLlu} onChange={(e) => setTimeoutLlu(e.target.value)} aria-label="Timeout LLU" />
      </Field>
      <Field label="OOM Increase MB:">
        <Input type="number" min={0} value={oomIncreaseMb} onChange={(e) => setOomIncreaseMb(e.target.value)} aria-label="OOM Increase MB" />
      </Field>

      <fieldset className="rounded-md border p-4">
        <legend className="px-1 text-sm font-medium">Tags</legend>
        <div className="grid grid-cols-2 gap-x-8 gap-y-2">
          {PREDEFINED_TAGS.map((tag) => (
            <label key={tag} className="flex items-center gap-2 text-sm">
              <Checkbox
                checked={selectedTags.has(tag)}
                onCheckedChange={(c) => toggleTag(tag, !!c)}
                disabled={useCustomTags}
                aria-label={tag}
              />
              {tag}
            </label>
          ))}
        </div>
      </fieldset>

      <div className="flex items-center gap-3">
        <label className="flex items-center gap-2 text-sm">
          <Checkbox
            checked={useCustomTags}
            onCheckedChange={(c) => setUseCustomTags(!!c)}
            aria-label="Custom Tags"
          />
          Custom Tags
        </label>
        <Input
          value={customTags}
          onChange={(e) => setCustomTags(e.target.value)}
          disabled={!useCustomTags}
          placeholder="space- or comma-separated tags"
          aria-label="Custom Tags value"
          className="flex-1"
        />
      </div>

      <div className="flex justify-end">
        <Button type="button" onClick={handleSaveClick}>
          Save
        </Button>
      </div>

      {/* CueGUI shows a facility-wide confirmation before persisting. The
          original references an internal team name; genericized here. */}
      <ConfirmDialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        title="Modify facility-wide service configuration?"
        description="You are about to modify a facility-wide service configuration. Are you authorized to change facility-wide service defaults?"
        confirmLabel="Yes"
        cancelLabel="No"
        onConfirm={handleConfirm}
      />
    </div>
  );
}
