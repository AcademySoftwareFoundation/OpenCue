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

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import type { Job } from "@/app/jobs/columns";
import type { Layer } from "@/app/layers/layer-columns";
import type { Frame } from "@/app/frames/frame-columns";
import {
  createDependOnFrame,
  createDependOnJob,
  createDependOnLayer,
  createFrameByFrameDepend,
  createFrameOnFrame,
  createFrameOnJob,
  createFrameOnLayer,
  createHardDepend,
  createLayerOnFrame,
  createLayerOnJob,
  createLayerOnLayer,
  createLayerOnSimFrame,
} from "@/app/utils/action_utils";
import {
  getFramesForJob,
  getJobsForRegex,
  getLayersForJob,
} from "@/app/utils/get_utils";
import { toastWarning } from "@/app/utils/notify_utils";

/**
 * "Dependency Wizard" dialog. Mounted once at the page level, opened
 * via the `cueweb:open-dependency-wizard` CustomEvent. Mirrors the full
 * CueGUI DependWizard: 12 dependency types with every picker rendered
 * as multi-select, just like CueGUI's QListWidget(ExtendedSelection).
 * Done fires the full cross-product of source x target picks in one
 * parallel batch via performAction.
 */

export const OPEN_DEPENDENCY_WIZARD_EVENT = "cueweb:open-dependency-wizard";

export type OpenDependencyWizardDetail = {
  job: Job;
  // Optional dependency type to preselect (e.g. opening the wizard from a
  // layer's "Dependency Wizard..." defaults to LAYER_ON_LAYER).
  initialType?: DependType;
};

type DependType =
  | "JOB_ON_JOB"
  | "JOB_ON_LAYER"
  | "JOB_ON_FRAME"
  | "JFBF"
  | "LAYER_ON_JOB"
  | "LAYER_ON_LAYER"
  | "LAYER_ON_FRAME"
  | "FRAME_BY_FRAME"
  | "FRAME_ON_JOB"
  | "FRAME_ON_LAYER"
  | "FRAME_ON_FRAME"
  | "LAYER_ON_SIM_FRAME";

type Step =
  | "type"
  | "sourceLayer"
  | "sourceFrame"
  | "targetJob"
  | "targetLayer"
  | "targetFrame"
  | "confirm";

type TypeConfig = {
  label: string;
  steps: Step[];
  // Optional client-side filter for the target layer picker. Used by
  // LAYER_ON_SIM_FRAME to restrict to simulation services.
  filterTargetLayer?: (l: Layer) => boolean;
};

const TYPE_CONFIG: Record<DependType, TypeConfig> = {
  JOB_ON_JOB: {
    label: "Job On Job (soft depend)",
    steps: ["type", "targetJob", "confirm"],
  },
  JOB_ON_LAYER: {
    label: "Job On Layer",
    steps: ["type", "targetJob", "targetLayer", "confirm"],
  },
  JOB_ON_FRAME: {
    label: "Job On Frame",
    steps: ["type", "targetJob", "targetLayer", "targetFrame", "confirm"],
  },
  JFBF: {
    label: "Frame By Frame for all layers (Hard Depend)",
    steps: ["type", "targetJob", "confirm"],
  },
  LAYER_ON_JOB: {
    label: "Layer On Job",
    steps: ["type", "sourceLayer", "targetJob", "confirm"],
  },
  LAYER_ON_LAYER: {
    label: "Layer On Layer",
    steps: ["type", "sourceLayer", "targetJob", "targetLayer", "confirm"],
  },
  LAYER_ON_FRAME: {
    label: "Layer On Frame",
    steps: ["type", "sourceLayer", "targetJob", "targetLayer", "targetFrame", "confirm"],
  },
  FRAME_BY_FRAME: {
    label: "Frame By Frame",
    steps: ["type", "sourceLayer", "targetJob", "targetLayer", "confirm"],
  },
  FRAME_ON_JOB: {
    label: "Frame On Job",
    steps: ["type", "sourceLayer", "sourceFrame", "targetJob", "confirm"],
  },
  FRAME_ON_LAYER: {
    label: "Frame On Layer",
    steps: ["type", "sourceLayer", "sourceFrame", "targetJob", "targetLayer", "confirm"],
  },
  FRAME_ON_FRAME: {
    label: "Frame On Frame",
    steps: ["type", "sourceLayer", "sourceFrame", "targetJob", "targetLayer", "targetFrame", "confirm"],
  },
  LAYER_ON_SIM_FRAME: {
    label: "Layer on Simulation Frame",
    steps: ["type", "sourceLayer", "targetJob", "targetLayer", "targetFrame", "confirm"],
    filterTargetLayer: (l) =>
      Array.isArray(l.services) &&
      l.services.some((s) => s.toLowerCase().includes("sim")),
  },
};

const TYPE_ORDER: DependType[] = [
  "JOB_ON_JOB",
  "JOB_ON_LAYER",
  "JOB_ON_FRAME",
  "JFBF",
  "LAYER_ON_JOB",
  "LAYER_ON_LAYER",
  "LAYER_ON_FRAME",
  "FRAME_BY_FRAME",
  "FRAME_ON_JOB",
  "FRAME_ON_LAYER",
  "FRAME_ON_FRAME",
  "LAYER_ON_SIM_FRAME",
];

function useDebounced<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = React.useState(value);
  React.useEffect(() => {
    const id = window.setTimeout(() => setDebounced(value), delayMs);
    return () => window.clearTimeout(id);
  }, [value, delayMs]);
  return debounced;
}

function toggle(set: Set<string>, id: string): Set<string> {
  const next = new Set(set);
  if (next.has(id)) next.delete(id);
  else next.add(id);
  return next;
}

function rangeSelect<T extends { id: string }>(
  items: T[],
  fromId: string | null,
  toId: string,
): Set<string> {
  if (!fromId) return new Set([toId]);
  const fromIdx = items.findIndex((i) => i.id === fromId);
  const toIdx = items.findIndex((i) => i.id === toId);
  if (fromIdx < 0 || toIdx < 0) return new Set([toId]);
  const [lo, hi] = fromIdx <= toIdx ? [fromIdx, toIdx] : [toIdx, fromIdx];
  return new Set(items.slice(lo, hi + 1).map((i) => i.id));
}

// Carry the parent-job name on layers / frames fetched across multiple
// upstream selections so the picker can show the right context.
type LayerWithParent = Layer & { parentJobName?: string };
type FrameWithParent = Frame & { parentJobName?: string };

export function DependencyWizardDialog() {
  const [open, setOpen] = React.useState(false);
  const [job, setJob] = React.useState<Job | null>(null);
  const [dependType, setDependType] = React.useState<DependType>("JOB_ON_JOB");

  const config = TYPE_CONFIG[dependType];
  const steps = config.steps;
  const [stepIdx, setStepIdx] = React.useState(0);
  const step: Step = steps[stepIdx] ?? "type";

  // Source-side state (within THIS job).
  const [sourceLayerResults, setSourceLayerResults] = React.useState<Layer[]>([]);
  const [sourceLayerLoading, setSourceLayerLoading] = React.useState(false);
  const [selectedSourceLayerIds, setSelectedSourceLayerIds] =
    React.useState<Set<string>>(new Set());
  const [sourceLayerAnchorId, setSourceLayerAnchorId] = React.useState<string | null>(null);

  const [sourceFrameResults, setSourceFrameResults] = React.useState<FrameWithParent[]>([]);
  const [sourceFrameLoading, setSourceFrameLoading] = React.useState(false);
  const [selectedSourceFrameIds, setSelectedSourceFrameIds] =
    React.useState<Set<string>>(new Set());
  const [sourceFrameAnchorId, setSourceFrameAnchorId] = React.useState<string | null>(null);

  // Target-side state.
  const [jobQuery, setJobQuery] = React.useState("");
  const debouncedJobQuery = useDebounced(jobQuery, 250);
  const [jobResults, setJobResults] = React.useState<Job[]>([]);
  const [jobsLoading, setJobsLoading] = React.useState(false);
  const [selectedTargetJobIds, setSelectedTargetJobIds] =
    React.useState<Set<string>>(new Set());
  const [targetJobAnchorId, setTargetJobAnchorId] = React.useState<string | null>(null);

  const [targetLayerResults, setTargetLayerResults] = React.useState<LayerWithParent[]>([]);
  const [targetLayerLoading, setTargetLayerLoading] = React.useState(false);
  const [selectedTargetLayerIds, setSelectedTargetLayerIds] =
    React.useState<Set<string>>(new Set());
  const [targetLayerAnchorId, setTargetLayerAnchorId] = React.useState<string | null>(null);

  const [targetFrameResults, setTargetFrameResults] = React.useState<FrameWithParent[]>([]);
  const [targetFrameLoading, setTargetFrameLoading] = React.useState(false);
  const [selectedTargetFrameIds, setSelectedTargetFrameIds] =
    React.useState<Set<string>>(new Set());
  const [targetFrameAnchorId, setTargetFrameAnchorId] = React.useState<string | null>(null);

  const [busy, setBusy] = React.useState(false);

  const selectedSourceLayers = React.useMemo(
    () => sourceLayerResults.filter((l) => selectedSourceLayerIds.has(l.id)),
    [sourceLayerResults, selectedSourceLayerIds],
  );
  const selectedSourceFrames = React.useMemo(
    () => sourceFrameResults.filter((f) => selectedSourceFrameIds.has(f.id)),
    [sourceFrameResults, selectedSourceFrameIds],
  );
  const selectedTargetJobs = React.useMemo(
    () => jobResults.filter((j) => selectedTargetJobIds.has(j.id)),
    [jobResults, selectedTargetJobIds],
  );
  const selectedTargetLayers = React.useMemo(
    () => targetLayerResults.filter((l) => selectedTargetLayerIds.has(l.id)),
    [targetLayerResults, selectedTargetLayerIds],
  );
  const selectedTargetFrames = React.useMemo(
    () => targetFrameResults.filter((f) => selectedTargetFrameIds.has(f.id)),
    [targetFrameResults, selectedTargetFrameIds],
  );

  // Set of selected source-layer names. Frames are scoped by layerName,
  // so a Set lookup is the cheap way to filter source frames once the
  // user has picked one or more source layers.
  const selectedSourceLayerNames = React.useMemo(
    () => new Set(selectedSourceLayers.map((l) => l.name)),
    [selectedSourceLayers],
  );
  const selectedTargetLayerNames = React.useMemo(
    () => new Set(selectedTargetLayers.map((l) => l.name)),
    [selectedTargetLayers],
  );

  function resetWizardState() {
    setStepIdx(0);
    setDependType("JOB_ON_JOB");
    setJobQuery("");
    setJobResults([]);
    setSelectedTargetJobIds(new Set());
    setTargetJobAnchorId(null);
    setSourceLayerResults([]);
    setSelectedSourceLayerIds(new Set());
    setSourceLayerAnchorId(null);
    setSourceFrameResults([]);
    setSelectedSourceFrameIds(new Set());
    setSourceFrameAnchorId(null);
    setTargetLayerResults([]);
    setSelectedTargetLayerIds(new Set());
    setTargetLayerAnchorId(null);
    setTargetFrameResults([]);
    setSelectedTargetFrameIds(new Set());
    setTargetFrameAnchorId(null);
    setBusy(false);
  }

  React.useEffect(() => {
    function handler(e: Event) {
      const detail = (e as CustomEvent<OpenDependencyWizardDetail>).detail;
      if (!detail?.job) return;
      setJob(detail.job);
      resetWizardState();
      if (detail.initialType) setDependType(detail.initialType);
      setOpen(true);
    }
    window.addEventListener(OPEN_DEPENDENCY_WIZARD_EVENT, handler);
    return () =>
      window.removeEventListener(OPEN_DEPENDENCY_WIZARD_EVENT, handler);
  }, []);

  // ----- Fetchers, all aggregating across multi-select upstream picks ---

  // Source layers in THIS job.
  React.useEffect(() => {
    if (!open || step !== "sourceLayer" || !job) return;
    let cancelled = false;
    setSourceLayerLoading(true);
    getLayersForJob(job)
      .then((layers) => {
        if (!cancelled) setSourceLayerResults(Array.isArray(layers) ? layers : []);
      })
      .finally(() => {
        if (!cancelled) setSourceLayerLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [open, step, job]);

  // Source frames: every frame in THIS job whose layerName is in the
  // selected source-layer set. One fetch, client-side filter.
  React.useEffect(() => {
    if (!open || step !== "sourceFrame" || !job) return;
    if (selectedSourceLayerNames.size === 0) return;
    let cancelled = false;
    setSourceFrameLoading(true);
    getFramesForJob(job)
      .then((frames) => {
        if (cancelled) return;
        setSourceFrameResults(
          frames.filter((f) => selectedSourceLayerNames.has(f.layerName)),
        );
      })
      .finally(() => {
        if (!cancelled) setSourceFrameLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [open, step, job, selectedSourceLayerNames]);

  // Target jobs: regex search.
  React.useEffect(() => {
    if (!open || step !== "targetJob") return;
    let cancelled = false;
    setJobsLoading(true);
    const regex = debouncedJobQuery.trim() || ".*";
    getJobsForRegex(regex, true)
      .then((jobs) => {
        if (!cancelled) setJobResults(Array.isArray(jobs) ? jobs.slice(0, 200) : []);
      })
      .finally(() => {
        if (!cancelled) setJobsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [open, step, debouncedJobQuery]);

  // Target layers: fetched in parallel from every selected target job,
  // concatenated. Each layer gets `parentJobName` so the picker can show
  // which job it came from when the user has multi-selected jobs.
  React.useEffect(() => {
    if (!open || step !== "targetLayer") return;
    if (selectedTargetJobs.length === 0) return;
    let cancelled = false;
    setTargetLayerLoading(true);
    Promise.all(
      selectedTargetJobs.map((j) =>
        getLayersForJob(j).then((layers) =>
          (Array.isArray(layers) ? layers : []).map((l) => ({ ...l, parentJobName: j.name })),
        ),
      ),
    )
      .then((arrs) => {
        if (cancelled) return;
        let merged: LayerWithParent[] = arrs.flat();
        if (config.filterTargetLayer) merged = merged.filter((l) => config.filterTargetLayer!(l));
        setTargetLayerResults(merged);
      })
      .finally(() => {
        if (!cancelled) setTargetLayerLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [open, step, selectedTargetJobs, config]);

  // Target frames: fetched in parallel from every unique parent job of
  // the selected target layers, then filtered to those layers.
  React.useEffect(() => {
    if (!open || step !== "targetFrame") return;
    if (selectedTargetLayers.length === 0) return;
    let cancelled = false;
    setTargetFrameLoading(true);
    const parentJobsByName = new Map<string, Job>();
    for (const l of selectedTargetLayers) {
      const j = selectedTargetJobs.find((tj) => tj.name === l.parentJobName);
      if (j && !parentJobsByName.has(j.name)) parentJobsByName.set(j.name, j);
    }
    Promise.all(
      Array.from(parentJobsByName.values()).map((j) =>
        getFramesForJob(j).then((frames) =>
          frames.map((f) => ({ ...f, parentJobName: j.name })),
        ),
      ),
    )
      .then((arrs) => {
        if (cancelled) return;
        const merged: FrameWithParent[] = arrs
          .flat()
          .filter((f) => selectedTargetLayerNames.has(f.layerName));
        setTargetFrameResults(merged);
      })
      .finally(() => {
        if (!cancelled) setTargetFrameLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [open, step, selectedTargetLayers, selectedTargetJobs, selectedTargetLayerNames]);

  // -------- Picker click handler (shared by every picker) --------

  function pickerClick<T extends { id: string }>(
    e: React.MouseEvent,
    items: T[],
    rowId: string,
    selected: Set<string>,
    setSelected: React.Dispatch<React.SetStateAction<Set<string>>>,
    anchorId: string | null,
    setAnchor: React.Dispatch<React.SetStateAction<string | null>>,
  ) {
    if (e.shiftKey) {
      setSelected(rangeSelect(items, anchorId, rowId));
      return;
    }
    // Cmd / Ctrl-click and plain click both toggle - more discoverable
    // on touch and saves users who don't realise Cmd is needed for
    // multi-select.
    setSelected(toggle(selected, rowId));
    setAnchor(rowId);
  }

  function advance() {
    setStepIdx((i) => Math.min(i + 1, steps.length - 1));
  }
  function goBack() {
    setStepIdx((i) => Math.max(i - 1, 0));
  }

  function handleContinue() {
    if (step === "type") {
      setSelectedSourceLayerIds(new Set());
      setSelectedSourceFrameIds(new Set());
      setSelectedTargetJobIds(new Set());
      setSelectedTargetLayerIds(new Set());
      setSelectedTargetFrameIds(new Set());
      advance();
      return;
    }
    if (step === "sourceLayer") {
      if (selectedSourceLayers.length === 0) {
        toastWarning("Pick at least one source layer to continue.");
        return;
      }
      advance();
      return;
    }
    if (step === "sourceFrame") {
      if (selectedSourceFrames.length === 0) {
        toastWarning("Pick at least one source frame to continue.");
        return;
      }
      advance();
      return;
    }
    if (step === "targetJob") {
      if (selectedTargetJobs.length === 0) {
        toastWarning("Pick at least one target job to continue.");
        return;
      }
      advance();
      return;
    }
    if (step === "targetLayer") {
      if (selectedTargetLayers.length === 0) {
        toastWarning("Pick at least one target layer to continue.");
        return;
      }
      advance();
      return;
    }
    if (step === "targetFrame") {
      if (selectedTargetFrames.length === 0) {
        toastWarning("Pick at least one target frame to continue.");
        return;
      }
      advance();
      return;
    }
  }

  async function handleDone() {
    if (!job) return;
    setBusy(true);
    try {
      const srcLayers = selectedSourceLayers.map((l) => ({ id: l.id, name: l.name }));
      const srcFrames = selectedSourceFrames.map((f) => ({ id: f.id, name: f.name }));
      const tgtJobs = selectedTargetJobs.map((j) => ({ id: j.id, name: j.name }));
      const tgtLayers = selectedTargetLayers.map((l) => ({ id: l.id, name: l.name }));
      const tgtFrames = selectedTargetFrames.map((f) => ({ id: f.id, name: f.name }));

      switch (dependType) {
        case "JOB_ON_JOB":
          await createDependOnJob(job, tgtJobs);
          break;
        case "JOB_ON_LAYER":
          await createDependOnLayer(job, tgtLayers);
          break;
        case "JOB_ON_FRAME":
          await createDependOnFrame(job, tgtFrames);
          break;
        case "JFBF": {
          // For each picked target job, fetch its layers and pair with
          // this job's layers by `layer.type`. createHardDepend then
          // collapses every matched pair across every target job into a
          // single bulk performAction.
          const [thisLayers, perTarget] = await Promise.all([
            getLayersForJob(job),
            Promise.all(
              selectedTargetJobs.map(async (j) => ({
                job: { id: j.id, name: j.name },
                layers: (await getLayersForJob(j)).map((l) => ({
                  id: l.id, name: l.name, type: l.type,
                })),
              })),
            ),
          ]);
          await createHardDepend(
            job,
            thisLayers.map((l) => ({ id: l.id, name: l.name, type: l.type })),
            perTarget,
          );
          break;
        }
        case "LAYER_ON_JOB":
          await createLayerOnJob(job, srcLayers, tgtJobs);
          break;
        case "LAYER_ON_LAYER":
          await createLayerOnLayer(job, srcLayers, tgtLayers);
          break;
        case "LAYER_ON_FRAME":
          await createLayerOnFrame(job, srcLayers, tgtFrames);
          break;
        case "FRAME_BY_FRAME":
          await createFrameByFrameDepend(job, srcLayers, tgtLayers, false);
          break;
        case "FRAME_ON_JOB":
          await createFrameOnJob(job, srcFrames, tgtJobs);
          break;
        case "FRAME_ON_LAYER":
          await createFrameOnLayer(job, srcFrames, tgtLayers);
          break;
        case "FRAME_ON_FRAME":
          await createFrameOnFrame(job, srcFrames, tgtFrames);
          break;
        case "LAYER_ON_SIM_FRAME": {
          // Fetch every frame in every source layer, filter to those
          // layers, then cross-product with the picked target sim
          // frames. CueGUI does the same fan-out client-side.
          const frames = await getFramesForJob(job);
          const sourceFrames = frames
            .filter((f) => selectedSourceLayerNames.has(f.layerName))
            .map((f) => ({ id: f.id, name: f.name }));
          await createLayerOnSimFrame(
            job,
            selectedSourceLayers.map((l) => l.name),
            sourceFrames,
            tgtFrames,
          );
          break;
        }
      }
      setOpen(false);
    } finally {
      setBusy(false);
    }
  }

  function continueDisabled(): boolean {
    if (busy) return true;
    switch (step) {
      case "sourceLayer":
        return selectedSourceLayers.length === 0;
      case "sourceFrame":
        return selectedSourceFrames.length === 0;
      case "targetJob":
        return selectedTargetJobs.length === 0;
      case "targetLayer":
        return selectedTargetLayers.length === 0;
      case "targetFrame":
        return selectedTargetFrames.length === 0;
      default:
        return false;
    }
  }

  const typeLabel = config.label;

  const multiHint = (
    <div className="text-xs text-foreground/60">
      Click to toggle a row. Shift-click for a range. Cmd/Ctrl-click also works.
    </div>
  );

  // Render a single picker block. Multi-select is always on now - the
  // hint and disabled-state both reflect that.
  function renderPicker<T extends { id: string; name: string }>({
    items,
    loading,
    selected,
    setSelected,
    anchor,
    setAnchor,
    rowExtra,
    emptyMsg,
  }: {
    items: T[];
    loading: boolean;
    selected: Set<string>;
    setSelected: React.Dispatch<React.SetStateAction<Set<string>>>;
    anchor: string | null;
    setAnchor: React.Dispatch<React.SetStateAction<string | null>>;
    rowExtra?: (item: T) => React.ReactNode;
    emptyMsg: string;
  }) {
    return (
      <>
        <div className="max-h-[40vh] overflow-auto rounded-md border border-input">
          {loading && <div className="px-3 py-2 text-center text-foreground/60">Loading...</div>}
          {!loading && items.length === 0 && (
            <div className="px-3 py-2 text-center text-foreground/60">{emptyMsg}</div>
          )}
          {!loading &&
            items.map((it) => (
              <button
                key={it.id}
                type="button"
                onClick={(e) =>
                  pickerClick(e, items, it.id, selected, setSelected, anchor, setAnchor)
                }
                className={`block w-full text-left px-3 py-1.5 font-mono text-xs border-b border-input/40 break-all ${
                  selected.has(it.id) ? "bg-foreground/10" : "hover:bg-foreground/[0.04]"
                }`}
              >
                {it.name}
                {rowExtra && <span className="text-foreground/60">{rowExtra(it)}</span>}
              </button>
            ))}
        </div>
        {multiHint}
        <div className="text-xs text-foreground/70">
          Selected: <span className="font-mono">{Array.from(selected).length}</span>
        </div>
      </>
    );
  }

  return (
    <Dialog open={open} onOpenChange={(o) => !busy && setOpen(o)}>
      <DialogContent className="sm:max-w-3xl">
        <DialogHeader>
          {step === "type" && (
            <>
              <DialogTitle>Select Dependency Type</DialogTitle>
              <DialogDescription>
                What type of dependency would you like this job to have?
              </DialogDescription>
            </>
          )}
          {step === "sourceLayer" && (
            <>
              <DialogTitle>Select Source Layer(s) in This Job</DialogTitle>
              <DialogDescription>
                Pick the layer(s) in{" "}
                <span className="font-mono">{job?.name ?? ""}</span> that should depend on the target.
              </DialogDescription>
            </>
          )}
          {step === "sourceFrame" && (
            <>
              <DialogTitle>Select Source Frame(s) in This Job</DialogTitle>
              <DialogDescription>
                Pick the frame(s) (from{" "}
                <span className="font-mono">{selectedSourceLayers.length}</span>{" "}
                source layer{selectedSourceLayers.length === 1 ? "" : "s"}) that should depend on the target.
              </DialogDescription>
            </>
          )}
          {step === "targetJob" && (
            <>
              <DialogTitle>Select Job(s) to Depend On</DialogTitle>
              <DialogDescription>
                Search for the target job(s). The list refreshes as you type.
              </DialogDescription>
            </>
          )}
          {step === "targetLayer" && (
            <>
              <DialogTitle>Select Target Layer(s) to Depend On</DialogTitle>
              <DialogDescription>
                Pick layer(s) across{" "}
                <span className="font-mono">{selectedTargetJobs.length}</span>{" "}
                target job{selectedTargetJobs.length === 1 ? "" : "s"}.
                {dependType === "LAYER_ON_SIM_FRAME" && " The list is restricted to simulation layers."}
              </DialogDescription>
            </>
          )}
          {step === "targetFrame" && (
            <>
              <DialogTitle>Select Target Frame(s) to Depend On</DialogTitle>
              <DialogDescription>
                Pick frame(s) from{" "}
                <span className="font-mono">{selectedTargetLayers.length}</span>{" "}
                target layer{selectedTargetLayers.length === 1 ? "" : "s"}.
              </DialogDescription>
            </>
          )}
          {step === "confirm" && (
            <>
              <DialogTitle>Confirmation</DialogTitle>
              <DialogDescription>Are you sure?</DialogDescription>
            </>
          )}
        </DialogHeader>

        {step === "type" && (
          <div className="grid gap-2 py-2 text-sm">
            <div className="text-foreground/70">
              This Job: <span className="font-mono break-all">{job?.name ?? ""}</span>
            </div>
            <div className="mt-2 grid gap-1">
              {TYPE_ORDER.map((t) => (
                <label key={t} className="flex items-center gap-2">
                  <input
                    type="radio"
                    name="cueweb-depend-type"
                    value={t}
                    checked={dependType === t}
                    onChange={() => setDependType(t)}
                  />
                  <span>{TYPE_CONFIG[t].label}</span>
                </label>
              ))}
            </div>
          </div>
        )}

        {step === "sourceLayer" && (
          <div className="grid gap-3 py-2 text-sm">
            <div className="text-foreground/70">
              This Job: <span className="font-mono break-all">{job?.name ?? ""}</span>
            </div>
            {renderPicker({
              items: sourceLayerResults,
              loading: sourceLayerLoading,
              selected: selectedSourceLayerIds,
              setSelected: setSelectedSourceLayerIds,
              anchor: sourceLayerAnchorId,
              setAnchor: setSourceLayerAnchorId,
              emptyMsg: "No layers found.",
            })}
          </div>
        )}

        {step === "sourceFrame" && (
          <div className="grid gap-3 py-2 text-sm">
            <div className="text-foreground/70">
              Source Layers:{" "}
              <span className="font-mono break-all">
                {selectedSourceLayers.map((l) => l.name).join(", ")}
              </span>
            </div>
            {renderPicker({
              items: sourceFrameResults,
              loading: sourceFrameLoading,
              selected: selectedSourceFrameIds,
              setSelected: setSelectedSourceFrameIds,
              anchor: sourceFrameAnchorId,
              setAnchor: setSourceFrameAnchorId,
              rowExtra: (f) => {
                const fr = f as unknown as Frame;
                const layerSuffix =
                  selectedSourceLayers.length > 1 ? ` [${fr.layerName}]` : "";
                return ` (${fr.state})${layerSuffix}`;
              },
              emptyMsg: "No frames found in those layers.",
            })}
          </div>
        )}

        {step === "targetJob" && (
          <div className="grid gap-3 py-2 text-sm">
            <div className="text-foreground/70">
              This Job: <span className="font-mono break-all">{job?.name ?? ""}</span>
            </div>
            <div className="flex items-center gap-3">
              <label htmlFor="cueweb-wizard-job-query" className="w-24 shrink-0 text-right text-foreground/70">
                Search:
              </label>
              <input
                id="cueweb-wizard-job-query"
                type="text"
                value={jobQuery}
                onChange={(e) => setJobQuery(e.target.value)}
                autoFocus
                className="flex-1 rounded-md border border-input bg-background px-3 py-1.5 text-sm"
                placeholder="regex match on job name (empty = all)"
              />
            </div>
            {renderPicker({
              items: jobResults,
              loading: jobsLoading,
              selected: selectedTargetJobIds,
              setSelected: setSelectedTargetJobIds,
              anchor: targetJobAnchorId,
              setAnchor: setTargetJobAnchorId,
              emptyMsg: "No jobs match.",
            })}
          </div>
        )}

        {step === "targetLayer" && (
          <div className="grid gap-3 py-2 text-sm">
            <div className="text-foreground/70">
              Depend on Job(s):{" "}
              <span className="font-mono break-all">
                {selectedTargetJobs.map((j) => j.name).join(", ")}
              </span>
            </div>
            {renderPicker({
              items: targetLayerResults,
              loading: targetLayerLoading,
              selected: selectedTargetLayerIds,
              setSelected: setSelectedTargetLayerIds,
              anchor: targetLayerAnchorId,
              setAnchor: setTargetLayerAnchorId,
              // When multiple target jobs are picked, annotate each row
              // with its parent job so the user can tell the duplicates
              // apart. With a single target job we skip the prefix to
              // keep the rows tight.
              rowExtra: (l) => {
                const ll = l as unknown as LayerWithParent;
                if (selectedTargetJobs.length > 1 && ll.parentJobName) return ` [${ll.parentJobName}]`;
                return null;
              },
              emptyMsg: dependType === "LAYER_ON_SIM_FRAME" ? "No simulation layers found." : "No layers found.",
            })}
          </div>
        )}

        {step === "targetFrame" && (
          <div className="grid gap-3 py-2 text-sm">
            <div className="text-foreground/70">
              Depend on Job(s):{" "}
              <span className="font-mono break-all">
                {selectedTargetJobs.map((j) => j.name).join(", ")}
              </span>
            </div>
            <div className="text-foreground/70">
              Depend on Layer(s):{" "}
              <span className="font-mono break-all">
                {selectedTargetLayers.map((l) => l.name).join(", ")}
              </span>
            </div>
            {renderPicker({
              items: targetFrameResults,
              loading: targetFrameLoading,
              selected: selectedTargetFrameIds,
              setSelected: setSelectedTargetFrameIds,
              anchor: targetFrameAnchorId,
              setAnchor: setTargetFrameAnchorId,
              rowExtra: (f) => {
                const fr = f as unknown as FrameWithParent;
                const parts: string[] = [`(${fr.state})`];
                if (selectedTargetLayers.length > 1) parts.push(`[${fr.layerName}]`);
                if (selectedTargetJobs.length > 1 && fr.parentJobName) parts.push(`<${fr.parentJobName}>`);
                return ` ${parts.join(" ")}`;
              },
              emptyMsg: "No frames found in those layers.",
            })}
          </div>
        )}

        {step === "confirm" && (
          <div className="grid gap-2 py-2 text-sm">
            <div>
              <span className="text-foreground/70">This Dependency type:</span>{" "}
              <span className="font-mono">{typeLabel}</span>
            </div>
            <div>
              <span className="text-foreground/70">This Job:</span>{" "}
              <span className="font-mono break-all">{job?.name ?? ""}</span>
            </div>
            {selectedSourceLayers.length > 0 && (
              <div>
                <span className="text-foreground/70">Source Layer{selectedSourceLayers.length > 1 ? "s" : ""}:</span>
                <ul className="ml-4 list-disc">
                  {selectedSourceLayers.map((l) => (
                    <li key={l.id} className="font-mono break-all">{l.name}</li>
                  ))}
                </ul>
              </div>
            )}
            {selectedSourceFrames.length > 0 && (
              <div>
                <span className="text-foreground/70">Source Frame{selectedSourceFrames.length > 1 ? "s" : ""}:</span>
                <ul className="ml-4 list-disc">
                  {selectedSourceFrames.map((f) => (
                    <li key={f.id} className="font-mono break-all">{f.name}</li>
                  ))}
                </ul>
              </div>
            )}
            <div className="mt-2 text-foreground/70">Depends on:</div>
            {selectedTargetJobs.length > 0 && (
              <ul className="ml-4 list-disc">
                {selectedTargetJobs.map((j) => (
                  <li key={j.id} className="font-mono break-all">Job: {j.name}</li>
                ))}
              </ul>
            )}
            {selectedTargetLayers.length > 0 && (
              <ul className="ml-4 list-disc">
                {selectedTargetLayers.map((l) => (
                  <li key={l.id} className="font-mono break-all">
                    Layer: {l.name}
                    {selectedTargetJobs.length > 1 && (l as LayerWithParent).parentJobName
                      ? ` [${(l as LayerWithParent).parentJobName}]`
                      : ""}
                  </li>
                ))}
              </ul>
            )}
            {selectedTargetFrames.length > 0 && (
              <ul className="ml-4 list-disc">
                {selectedTargetFrames.map((f) => (
                  <li key={f.id} className="font-mono break-all">Frame: {f.name}</li>
                ))}
              </ul>
            )}
            {dependType === "JFBF" && (
              <div className="mt-2 text-xs text-foreground/60">
                For each target job, the wizard will match each layer in this job to a same-typed layer in the target and create one Frame-By-Frame depend per matched pair.
              </div>
            )}
          </div>
        )}

        <DialogFooter>
          {step === "type" && (
            <Button type="button" variant="outline" onClick={() => setOpen(false)} disabled={busy}>
              Cancel
            </Button>
          )}
          {step !== "type" && (
            <Button type="button" variant="outline" onClick={goBack} disabled={busy}>
              Go Back
            </Button>
          )}
          {step !== "confirm" && (
            <Button type="button" onClick={handleContinue} disabled={continueDisabled()}>
              Continue
            </Button>
          )}
          {step === "confirm" && (
            <Button type="button" onClick={handleDone} disabled={busy}>
              {busy ? "Saving..." : "Done"}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
