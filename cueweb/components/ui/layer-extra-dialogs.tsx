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

import type { Frame } from "@/app/frames/frame-columns";
import type { Job } from "@/app/jobs/columns";
import type { Layer } from "@/app/layers/layer-columns";
import {
  eatAndMarkdoneLayers,
  fetchLayerDepends,
  markdoneLayers,
  reorderLayerFrames,
  setLayerMinCores,
  setLayerMinGpuMemory,
  setLayerMinMemory,
  setLayerTags,
  setLayerThreadable,
  staggerLayerFrames,
} from "@/app/utils/action_utils";
import { getFramesForJob } from "@/app/utils/get_utils";
import { convertMemoryToString, secondsToHHMMSS } from "@/app/utils/layers_frames_utils";
import { handleError } from "@/app/utils/notify_utils";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Status } from "@/components/ui/status";
import { OPEN_DEPENDENCY_WIZARD_EVENT } from "@/components/ui/dependency-wizard-dialog";

const KB_PER_GB = 1048576;
const SELECT_CLASS =
  "h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-ring";

function layerOf(e: Event): Layer | null {
  return (e as CustomEvent<{ layer?: Layer }>).detail?.layer ?? null;
}

// Reorder a single layer's frames. Mirrors the job Reorder dialog; the range
// defaults to the layer's own frame range.
function LayerReorderFramesDialog() {
  const [open, setOpen] = React.useState(false);
  const [layer, setLayer] = React.useState<Layer | null>(null);
  const [range, setRange] = React.useState("");
  const [order, setOrder] = React.useState<"FIRST" | "LAST" | "REVERSE">("FIRST");
  const [busy, setBusy] = React.useState(false);

  React.useEffect(() => {
    function handler(e: Event) {
      const l = layerOf(e);
      if (!l) return;
      setLayer(l);
      setRange(l.range ?? "");
      setOrder("FIRST");
      setOpen(true);
    }
    window.addEventListener("cueweb:open-layer-reorder", handler);
    return () => window.removeEventListener("cueweb:open-layer-reorder", handler);
  }, []);

  async function apply() {
    if (!layer || !range.trim()) return;
    setBusy(true);
    try {
      if (await reorderLayerFrames(layer, range.trim(), order)) setOpen(false);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Reorder Frames</DialogTitle>
        </DialogHeader>
        <div className="min-w-0 space-y-3 py-2 text-sm">
          <p className="break-all font-mono text-xs text-muted-foreground">{layer?.name}</p>
          <label className="block min-w-0">
            <span className="text-muted-foreground">Frame range</span>
            <Input value={range} onChange={(e) => setRange(e.target.value)} className="mt-1 w-full" placeholder="e.g. 1-100" />
          </label>
          <label className="block min-w-0">
            <span className="text-muted-foreground">Order</span>
            <select value={order} onChange={(e) => setOrder(e.target.value as "FIRST" | "LAST" | "REVERSE")} className={SELECT_CLASS} aria-label="Order">
              <option value="FIRST">FIRST</option>
              <option value="LAST">LAST</option>
              <option value="REVERSE">REVERSE</option>
            </select>
          </label>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
          <Button onClick={apply} disabled={busy || !range.trim()}>OK</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function LayerStaggerFramesDialog() {
  const [open, setOpen] = React.useState(false);
  const [layer, setLayer] = React.useState<Layer | null>(null);
  const [range, setRange] = React.useState("");
  const [increment, setIncrement] = React.useState("1");
  const [busy, setBusy] = React.useState(false);

  React.useEffect(() => {
    function handler(e: Event) {
      const l = layerOf(e);
      if (!l) return;
      setLayer(l);
      setRange(l.range ?? "");
      setIncrement("1");
      setOpen(true);
    }
    window.addEventListener("cueweb:open-layer-stagger", handler);
    return () => window.removeEventListener("cueweb:open-layer-stagger", handler);
  }, []);

  async function apply() {
    if (!layer || !range.trim()) return;
    const inc = Number.parseInt(increment, 10);
    if (!Number.isFinite(inc) || inc < 1) return;
    setBusy(true);
    try {
      if (await staggerLayerFrames(layer, range.trim(), inc)) setOpen(false);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Stagger Frames</DialogTitle>
        </DialogHeader>
        <div className="min-w-0 space-y-3 py-2 text-sm">
          <p className="break-all font-mono text-xs text-muted-foreground">{layer?.name}</p>
          <label className="block min-w-0">
            <span className="text-muted-foreground">Frame range</span>
            <Input value={range} onChange={(e) => setRange(e.target.value)} className="mt-1 w-full" placeholder="e.g. 1-100" />
          </label>
          <label className="block min-w-0">
            <span className="text-muted-foreground">Increment</span>
            <Input type="number" min={1} value={increment} onChange={(e) => setIncrement(e.target.value)} className="mt-1 w-full" />
          </label>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
          <Button onClick={apply} disabled={busy || !range.trim()}>OK</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// Mark done / Eat and Mark done confirmation (CueGUI questionBoxYesNo). Both
// are destructive, so we confirm before firing - matching CueGUI's prompt.
function LayerConfirmDialog() {
  const [open, setOpen] = React.useState(false);
  const [layer, setLayer] = React.useState<Layer | null>(null);
  const [action, setAction] = React.useState<"markdone" | "eatandmarkdone">("markdone");
  const [busy, setBusy] = React.useState(false);

  React.useEffect(() => {
    function handler(e: Event) {
      const detail = (e as CustomEvent<{ layer?: Layer; action?: "markdone" | "eatandmarkdone" }>).detail;
      if (!detail?.layer) return;
      setLayer(detail.layer);
      setAction(detail.action ?? "markdone");
      setOpen(true);
    }
    window.addEventListener("cueweb:open-layer-confirm", handler);
    return () => window.removeEventListener("cueweb:open-layer-confirm", handler);
  }, []);

  const title = action === "eatandmarkdone" ? "Eat and Mark done" : "Mark done";
  const question =
    action === "eatandmarkdone"
      ? "Eat ALL frames in this layer and mark them done?"
      : "Mark done ALL frames in this layer?";

  async function confirm() {
    if (!layer) return;
    setBusy(true);
    try {
      const ok = action === "eatandmarkdone" ? await eatAndMarkdoneLayers([layer]) : await markdoneLayers([layer]);
      if (ok) setOpen(false);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>{question}</DialogDescription>
        </DialogHeader>
        <p className="break-all font-mono text-xs text-muted-foreground">{layer?.name}</p>
        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
          <Button variant="destructive" onClick={confirm} disabled={busy}>{title}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// Normalize + de-dupe a tag list (trim, drop empties, preserve order).
function cleanTags(tags: string[]): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const t of tags) {
    const v = t.trim();
    if (v && !seen.has(v)) {
      seen.add(v);
      out.push(v);
    }
  }
  return out;
}

function sameTags(a: string[], b: string[]): boolean {
  return a.length === b.length && a.every((t, i) => t === b[i]);
}

// Layer Properties (CueGUI LayerPropertiesDialog + LayerTagsDialog). Editable:
// min cores, min memory (GB), min GPU memory (GB), threadable, and tags. Other
// attributes are shown read-only for context.
function LayerPropertiesDialog() {
  const [open, setOpen] = React.useState(false);
  const [layer, setLayer] = React.useState<Layer | null>(null);
  const [minCores, setMinCores] = React.useState("");
  const [minMemoryGb, setMinMemoryGb] = React.useState("");
  const [minGpuMemoryGb, setMinGpuMemoryGb] = React.useState("");
  const [threadable, setThreadable] = React.useState(false);
  const [tags, setTags] = React.useState<string[]>([]);
  const [tagDraft, setTagDraft] = React.useState("");
  const [busy, setBusy] = React.useState(false);

  React.useEffect(() => {
    function handler(e: Event) {
      const l = layerOf(e);
      if (!l) return;
      setLayer(l);
      setMinCores(String(l.minCores ?? 0));
      setMinMemoryGb((Number.parseInt(l.minMemory) / KB_PER_GB || 0).toFixed(2));
      setMinGpuMemoryGb((Number.parseInt(l.minGpuMemory) / KB_PER_GB || 0).toFixed(2));
      setThreadable(!!l.isThreadable);
      setTags(cleanTags(l.tags ?? []));
      setTagDraft("");
      setOpen(true);
    }
    window.addEventListener("cueweb:open-layer-properties", handler);
    return () => window.removeEventListener("cueweb:open-layer-properties", handler);
  }, []);

  // Add the draft (supports comma/space separated entry) to the tag list.
  function commitTagDraft() {
    const parts = tagDraft.split(/[,\s]+/);
    if (parts.some((p) => p.trim())) setTags((prev) => cleanTags([...prev, ...parts]));
    setTagDraft("");
  }
  function removeTag(tag: string) {
    setTags((prev) => prev.filter((t) => t !== tag));
  }

  async function apply() {
    if (!layer) return;
    setBusy(true);
    try {
      const tasks: Promise<boolean>[] = [];

      const cores = Number.parseFloat(minCores);
      if (Number.isFinite(cores) && cores !== layer.minCores) tasks.push(setLayerMinCores(layer, cores));

      const memGb = Number.parseFloat(minMemoryGb);
      const memKb = Math.round(memGb * KB_PER_GB);
      if (Number.isFinite(memGb) && memKb !== Number.parseInt(layer.minMemory)) tasks.push(setLayerMinMemory(layer, memKb));

      const gpuGb = Number.parseFloat(minGpuMemoryGb);
      const gpuKb = Math.round(gpuGb * KB_PER_GB);
      if (Number.isFinite(gpuGb) && gpuKb !== Number.parseInt(layer.minGpuMemory)) tasks.push(setLayerMinGpuMemory(layer, gpuKb));

      if (threadable !== !!layer.isThreadable) tasks.push(setLayerThreadable(layer, threadable));

      // Fold any uncommitted draft text into the tags before comparing.
      const finalTags = cleanTags([...tags, ...tagDraft.split(/[,\s]+/)]);
      if (!sameTags(finalTags, cleanTags(layer.tags ?? []))) tasks.push(setLayerTags(layer, finalTags));

      if (tasks.length === 0) {
        setOpen(false);
        return;
      }
      const results = await Promise.all(tasks);
      if (results.every(Boolean)) setOpen(false);
    } catch (error) {
      handleError(error, "Could not update layer properties");
    } finally {
      setBusy(false);
    }
  }

  // Suggest tags already in use on this layer (datalist) so re-adding a
  // removed tag is quick. (CueGUI seeds from the show's existing tags.)
  const tagSuggestions = cleanTags(layer?.tags ?? []);

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Layer Properties</DialogTitle>
          <DialogDescription className="break-all font-mono text-xs">{layer?.name}</DialogDescription>
        </DialogHeader>
        <div className="min-w-0 space-y-4 py-2 text-sm">
          <div className="grid min-w-0 grid-cols-2 gap-3">
            <label className="min-w-0">
              <span className="text-muted-foreground">Min cores</span>
              <Input type="number" min={0} step="0.01" value={minCores} onChange={(e) => setMinCores(e.target.value)} className="mt-1 w-full" />
            </label>
            <label className="min-w-0">
              <span className="text-muted-foreground">Min memory (GB)</span>
              <Input type="number" min={0} step="0.1" value={minMemoryGb} onChange={(e) => setMinMemoryGb(e.target.value)} className="mt-1 w-full" />
            </label>
            <label className="min-w-0">
              <span className="text-muted-foreground">Min GPU memory (GB)</span>
              <Input type="number" min={0} step="0.1" value={minGpuMemoryGb} onChange={(e) => setMinGpuMemoryGb(e.target.value)} className="mt-1 w-full" />
            </label>
            <label className="flex min-w-0 items-center gap-2 pt-6">
              <Checkbox checked={threadable} onCheckedChange={(v) => setThreadable(!!v)} aria-label="Threadable" />
              <span className="text-muted-foreground">Threadable</span>
            </label>
          </div>

          {/* Tags editor (CueGUI LayerTagsDialog): removable chips + an input
              that accepts comma/space separated entries; Enter or "Add" commits. */}
          <div className="min-w-0">
            <span className="text-muted-foreground">Tags</span>
            <div className="mt-1 flex flex-wrap items-center gap-1.5 rounded-md border border-input p-2">
              {tags.length === 0 ? (
                <span className="text-xs text-muted-foreground">No tags</span>
              ) : (
                tags.map((t) => (
                  <span key={t} className="inline-flex items-center gap-1 rounded bg-muted px-1.5 py-0.5 font-mono text-xs">
                    {t}
                    <button
                      type="button"
                      aria-label={`Remove tag ${t}`}
                      className="text-muted-foreground hover:text-foreground"
                      onClick={() => removeTag(t)}
                    >
                      ×
                    </button>
                  </span>
                ))
              )}
            </div>
            <div className="mt-1.5 flex items-center gap-2">
              <Input
                list="layer-tag-suggestions"
                value={tagDraft}
                onChange={(e) => setTagDraft(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === ",") {
                    e.preventDefault();
                    commitTagDraft();
                  }
                }}
                placeholder="Add a tag, then Enter"
                aria-label="Add tag"
                className="h-8 w-full"
              />
              <Button type="button" variant="outline" size="sm" onClick={commitTagDraft} disabled={!tagDraft.trim()}>
                Add
              </Button>
              <datalist id="layer-tag-suggestions">
                {tagSuggestions.map((t) => (
                  <option key={t} value={t} />
                ))}
              </datalist>
            </div>
          </div>

          {layer ? (
            <dl className="grid grid-cols-2 gap-x-4 gap-y-1 rounded-md border border-input p-3 text-xs">
              <dt className="text-muted-foreground">Range</dt>
              <dd className="break-all font-mono">{layer.range || "-"}</dd>
              <dt className="text-muted-foreground">Services</dt>
              <dd className="break-all font-mono">{(layer.services ?? []).join(", ") || "-"}</dd>
              <dt className="text-muted-foreground">Limits</dt>
              <dd className="break-all font-mono">{(layer.limits ?? []).join(", ") || "-"}</dd>
              <dt className="text-muted-foreground">Max cores</dt>
              <dd className="font-mono">{layer.maxCores}</dd>
              <dt className="text-muted-foreground">Min / Max GPUs</dt>
              <dd className="font-mono">{layer.minGpus} / {layer.maxGpus}</dd>
              <dt className="text-muted-foreground">Timeout (min)</dt>
              <dd className="font-mono">{layer.timeout}</dd>
            </dl>
          ) : null}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
          <Button onClick={apply} disabled={busy}>OK</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// View Dependencies for a layer (CueGUI DependDialog -> getWhatThisDependsOn).
function LayerDependenciesDialog() {
  const [open, setOpen] = React.useState(false);
  const [layer, setLayer] = React.useState<Layer | null>(null);
  const [depends, setDepends] = React.useState<any[]>([]);
  const [loading, setLoading] = React.useState(false);

  const load = React.useCallback(async (l: Layer) => {
    setLoading(true);
    try {
      setDepends(await fetchLayerDepends(l));
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    function handler(e: Event) {
      const l = layerOf(e);
      if (!l) return;
      setLayer(l);
      setDepends([]);
      setOpen(true);
      load(l);
    }
    window.addEventListener("cueweb:open-layer-dependencies", handler);
    return () => window.removeEventListener("cueweb:open-layer-dependencies", handler);
  }, [load]);

  const onJobOf = (d: any) => d.dependOnJob ?? d.depend_on_job ?? "";
  const onLayerOf = (d: any) => d.dependOnLayer ?? d.depend_on_layer ?? "";
  const onFrameOf = (d: any) => d.dependOnFrame ?? d.depend_on_frame ?? "";

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="sm:max-w-4xl">
        <DialogHeader>
          <DialogTitle>
            <span className="break-all font-mono">Dependencies for Layer: {layer?.name ?? ""}</span>
          </DialogTitle>
          <DialogDescription>
            Each row is a depend this layer depends on (getWhatThisDependsOn). Type matches
            depend.DependType; Target is INTERNAL or EXTERNAL; Active indicates whether the
            depend is still blocking.
          </DialogDescription>
        </DialogHeader>
        <div className="max-h-[55vh] overflow-auto rounded-md border border-input text-xs">
          <table className="w-full table-auto">
            <thead className="sticky top-0 bg-foreground/[0.04]">
              <tr className="text-left">
                <th className="px-3 py-2">Type</th>
                <th className="px-3 py-2">Target</th>
                <th className="px-3 py-2">Active</th>
                <th className="px-3 py-2">OnJob</th>
                <th className="px-3 py-2">OnLayer</th>
                <th className="px-3 py-2">OnFrame</th>
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr><td colSpan={6} className="px-3 py-4 text-center text-foreground/60">Loading dependencies...</td></tr>
              )}
              {!loading && depends.length === 0 && (
                <tr><td colSpan={6} className="px-3 py-4 text-center text-foreground/60">This layer has no dependencies.</td></tr>
              )}
              {!loading && depends.map((d, i) => (
                <tr key={d.id ?? i} className="border-t border-input/60">
                  <td className="px-3 py-1.5 font-mono">{d.type ?? ""}</td>
                  <td className="px-3 py-1.5 font-mono">{d.target ?? ""}</td>
                  <td className="px-3 py-1.5 font-mono">{d.active === undefined ? "" : String(d.active)}</td>
                  <td className="px-3 py-1.5 break-all font-mono">{onJobOf(d)}</td>
                  <td className="px-3 py-1.5 break-all font-mono">{onLayerOf(d)}</td>
                  <td className="px-3 py-1.5 break-all font-mono">{onFrameOf(d)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => layer && load(layer)} disabled={loading || !layer}>Refresh</Button>
          <Button onClick={() => setOpen(false)}>Close</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// View Processes (CueGUI FrameActions.viewProcesses applied to a layer): the
// frames in this layer that are currently RUNNING, with host + runtime. Frames
// are fetched from the parent job and filtered client-side by layer name.
function LayerProcessesDialog({ job }: { job?: Job }) {
  const [open, setOpen] = React.useState(false);
  const [layer, setLayer] = React.useState<Layer | null>(null);
  const [frames, setFrames] = React.useState<Frame[]>([]);
  const [loading, setLoading] = React.useState(false);

  const load = React.useCallback(
    async (l: Layer) => {
      if (!job) return;
      setLoading(true);
      try {
        const all = await getFramesForJob(job);
        setFrames(all.filter((f) => f.layerName === l.name && f.state === "RUNNING"));
      } catch (error) {
        handleError(error, "Could not load layer processes");
      } finally {
        setLoading(false);
      }
    },
    [job],
  );

  React.useEffect(() => {
    function handler(e: Event) {
      const l = layerOf(e);
      if (!l) return;
      setLayer(l);
      setFrames([]);
      setOpen(true);
      load(l);
    }
    window.addEventListener("cueweb:open-layer-processes", handler);
    return () => window.removeEventListener("cueweb:open-layer-processes", handler);
  }, [load]);

  const nowSec = Math.floor(Date.now() / 1000);
  const hostOf = (f: Frame) => (f.lastResource ? f.lastResource.split("/")[0] : "-");

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="sm:max-w-3xl">
        <DialogHeader>
          <DialogTitle>
            <span className="break-all font-mono">Processes: {layer?.name ?? ""}</span>
          </DialogTitle>
          <DialogDescription>Frames in this layer that are currently running.</DialogDescription>
        </DialogHeader>
        <div className="max-h-[55vh] overflow-auto rounded-md border border-input text-xs">
          <table className="w-full table-auto">
            <thead className="sticky top-0 bg-foreground/[0.04]">
              <tr className="text-left">
                <th className="px-3 py-2">Frame</th>
                <th className="px-3 py-2">State</th>
                <th className="px-3 py-2">Host</th>
                <th className="px-3 py-2">Runtime</th>
                <th className="px-3 py-2">Memory</th>
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr><td colSpan={5} className="px-3 py-4 text-center text-foreground/60">Loading processes...</td></tr>
              )}
              {!loading && frames.length === 0 && (
                <tr><td colSpan={5} className="px-3 py-4 text-center text-foreground/60">No running frames in this layer.</td></tr>
              )}
              {!loading && frames.map((f) => (
                <tr key={f.id} className="border-t border-input/60">
                  <td className="px-3 py-1.5 break-all font-mono">{f.name}</td>
                  <td className="px-3 py-1.5"><Status status={f.state} /></td>
                  <td className="px-3 py-1.5 break-all font-mono">{hostOf(f)}</td>
                  <td className="px-3 py-1.5 font-mono">{f.startTime ? secondsToHHMMSS(Math.max(0, nowSec - f.startTime)) : "-"}</td>
                  <td className="px-3 py-1.5 font-mono">{convertMemoryToString(Number.parseInt(f.usedMemory), JSON.stringify(f))}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => layer && load(layer)} disabled={loading || !layer || !job}>Refresh</Button>
          <Button onClick={() => setOpen(false)}>Close</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// Mounts every layer-menu dialog once. Place on any page that renders a
// layers table (the job detail Layers tab). `job` powers View Processes and
// the layer Dependency Wizard.
export function LayerExtraDialogs({ job }: { job?: Job }) {
  // A layer's "Dependency Wizard..." reuses the full job Dependency Wizard,
  // preselected to LAYER_ON_LAYER. Bridge the layer-scoped event to the
  // wizard's own open event, supplying the parent job it operates on. The
  // DependencyWizardDialog itself is mounted once per page (by the jobs
  // data-table on Monitor Jobs, or by the job detail page)
  React.useEffect(() => {
    function handler() {
      if (!job) return;
      window.dispatchEvent(
        new CustomEvent(OPEN_DEPENDENCY_WIZARD_EVENT, {
          detail: { job, initialType: "LAYER_ON_LAYER" },
        }),
      );
    }
    window.addEventListener("cueweb:open-layer-depend-wizard", handler);
    return () => window.removeEventListener("cueweb:open-layer-depend-wizard", handler);
  }, [job]);

  return (
    <>
      <LayerReorderFramesDialog />
      <LayerStaggerFramesDialog />
      <LayerConfirmDialog />
      <LayerPropertiesDialog />
      <LayerDependenciesDialog />
      <LayerProcessesDialog job={job} />
    </>
  );
}
