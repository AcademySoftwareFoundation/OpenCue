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
import { Frame, frameColumns } from "@/app/frames/frame-columns";
import { Job } from "@/app/jobs/columns";
import { Layer, layerColumns } from "@/app/layers/layer-columns";
import { getFramesForJob, getLayersForJob } from "@/app/utils/get_utils";
import { handleError } from "@/app/utils/notify_utils";
import { setAttributeSelection } from "@/app/utils/use_attribute_selection";
import { useShowDependencyGraph } from "@/app/utils/use_show_dependency_graph";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { ChevronDown, ChevronRight, Inbox, X } from "lucide-react";
import { JobDependencyGraph } from "./job-dependency-graph";
import { FrameExtraDialogs } from "./frame-extra-dialogs";
import { FramePreviewPanel } from "./frame-preview-panel";
import { FrameRangeSelector } from "./frame-range-selector";
import { LayerExtraDialogs } from "./layer-extra-dialogs";
import { SimpleDataTable } from "./simple-data-table";

/**
 * Inline replacement for the previous popup-only Layers + Frames view.
 *
 * Renders the layers table and the frames table for the currently selected
 * job, stacked vertically below the jobs table. Mirrors the CueGUI Monitor
 * Jobs + Monitor Job Details dock layout: pick a job row above and its
 * layers fill the middle panel, frames fill the bottom panel. Both panels
 * re-fetch every 5s while the same job stays selected, with a `cancelled`
 * flag guarding against stale responses on selection change.
 *
 * Stays empty (with a friendly hint) when no job is selected.
 */
export interface JobDetailsInlineProps {
  job: Job | null;
  username: string;
}

export function JobDetailsInline({ job, username }: JobDetailsInlineProps) {
  const [layers, setLayers] = React.useState<Layer[]>([]);
  const [frames, setFrames] = React.useState<Frame[]>([]);
  const [loadingLayers, setLoadingLayers] = React.useState(false);
  const [loadingFrames, setLoadingFrames] = React.useState(false);

  // Layer-click drives two side-effects:
  //   1. Filter the Frames table to that layer (frame.layerName == layer.name).
  //   2. Push the layer payload into the Attributes panel (right dock).
  // Clicking the same layer again toggles the filter off and reverts the
  // attributes panel to the parent job (so the panel always reflects the
  // most-relevant selection).
  const [selectedLayer, setSelectedLayer] = React.useState<Layer | null>(null);
  // Frame row clicked into the Attributes panel (single-click). Double-click
  // still opens the log viewer; this only drives the panel + row highlight.
  const [selectedFrame, setSelectedFrame] = React.useState<Frame | null>(null);

  // Dependency graph panel visibility. The shared hook persists in
  // localStorage AND broadcasts a CustomEvent so the Cuetopia > View
  // Job Graph menu entry can flip it without a URL navigation - which
  // wouldn't fire a second time because the URL would already be set.
  const { show: showGraph, toggle: toggleGraph } = useShowDependencyGraph();

  // Clear stale rows when the parent selects a different job so the
  // previous job's data doesn't briefly flash in the new context.
  React.useEffect(() => {
    setLayers([]);
    setFrames([]);
    // Reset the layer filter when the parent job changes; the new job's
    // layer set is unrelated to the previous one.
    setSelectedLayer(null);
  }, [job?.id]);

  // Layer-click handler: toggle the filter + sync the Attributes panel.
  const handleLayerClick = React.useCallback(
    (layer: Layer) => {
      setSelectedLayer((prev) => {
        const isToggleOff = prev?.id === layer.id;
        if (isToggleOff) {
          // Re-select the parent job in the Attributes panel so the panel
          // doesn't go blank when the user unfilters.
          if (job) {
            setAttributeSelection({
              type: "job",
              id: job.id,
              name: job.name,
              data: job as unknown as Record<string, unknown>,
            });
          }
          return null;
        }
        setAttributeSelection({
          type: "layer",
          id: layer.id,
          name: layer.name,
          data: layer as unknown as Record<string, unknown>,
        });
        return layer;
      });
    },
    [job],
  );

  // If the selected layer disappears (e.g. job switched, layer removed by
  // the next poll), clear it so the frames filter doesn't leave the table
  // empty for a stale reason.
  React.useEffect(() => {
    if (!selectedLayer) return;
    const stillPresent = layers.some((l) => l.id === selectedLayer.id);
    if (!stillPresent) setSelectedLayer(null);
  }, [layers, selectedLayer]);

  // Frame-click handler: load the frame into the Attributes panel and highlight
  // the row. Idempotent (re-selecting the same frame is a no-op), so a
  // double-click - which fires two single-clicks before opening the log viewer -
  // doesn't flicker the panel. Switching to a different layer/job re-selects
  // that entity via the effects above / the layer-click handler.
  const handleFrameClick = React.useCallback((frame: Frame) => {
    setSelectedFrame(frame);
    setAttributeSelection({
      type: "frame",
      id: frame.id,
      name: frame.name,
      data: frame as unknown as Record<string, unknown>,
    });
  }, []);

  // Clear the frame highlight when the job or the filtered layer changes (the
  // visible frame set changes underneath it).
  React.useEffect(() => {
    setSelectedFrame(null);
  }, [job?.id, selectedLayer?.id]);

  // Drop the highlight if the selected frame is no longer present after a poll.
  React.useEffect(() => {
    if (!selectedFrame) return;
    const stillPresent = frames.some((fr) => fr.id === selectedFrame.id);
    if (!stillPresent) setSelectedFrame(null);
  }, [frames, selectedFrame]);

  // The layer menu's "View Layer" (and the frame menu's "Filter Selected
  // Layers") dispatch `cueweb:view-layer`. Apply the same filter the
  // row-click toggle uses so the Frames table narrows to that layer.
  React.useEffect(() => {
    function handler(e: Event) {
      const layer = (e as CustomEvent<{ layer?: Layer }>).detail?.layer;
      if (!layer?.name) return;
      // Prefer the live layer object from the current poll (keeps id stable
      // for the selected-row highlight); fall back to the event payload.
      const match = layers.find((l) => l.name === layer.name) ?? layer;
      setSelectedLayer(match);
      setAttributeSelection({
        type: "layer",
        id: match.id,
        name: match.name,
        data: match as unknown as Record<string, unknown>,
      });
    }
    window.addEventListener("cueweb:view-layer", handler);
    return () => window.removeEventListener("cueweb:view-layer", handler);
  }, [layers]);

  React.useEffect(() => {
    if (!job) return;

    let cancelled = false;
    // Serialize polls: a slow request must not be overtaken by a newer one
    // and stomp on fresher layer/frame state when it finally resolves.
    let inFlight = false;

    const load = async (initial: boolean) => {
      if (inFlight) return;
      inFlight = true;
      try {
        if (initial) {
          setLoadingLayers(true);
          setLoadingFrames(true);
        }
        const [nextLayers, nextFrames] = await Promise.all([
          getLayersForJob(job),
          getFramesForJob(job),
        ]);
        if (cancelled) return;
        setLayers(nextLayers);
        setFrames(nextFrames);
      } catch (err) {
        if (!cancelled) handleError(err, "Error refreshing job details");
      } finally {
        inFlight = false;
        if (!cancelled) {
          setLoadingLayers(false);
          setLoadingFrames(false);
        }
      }
    };

    load(true);
    const interval = setInterval(() => void load(false), 5000);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [job?.id, job]);

  if (!job) {
    return (
      <section
        aria-label="Job details"
        className="mt-4 rounded-md border border-border"
      >
        <EmptyState
          icon={<Inbox className="h-6 w-6" aria-hidden="true" />}
          title="No job selected"
          description="Click a row in the jobs table above to view its layers and frames here."
          className="py-8"
        />
      </section>
    );
  }

  return (
    <section aria-label={`Details for ${job.name}`} className="mt-4 space-y-4">
      <header className="flex flex-wrap items-baseline justify-between gap-2 rounded-md border border-border bg-muted/40 px-3 py-2">
        <div className="min-w-0">
          <h2 className="truncate text-sm font-semibold" title={job.name}>
            {job.name}
          </h2>
          <p className="text-xs text-muted-foreground">
            {layers.length} layer{layers.length === 1 ? "" : "s"} - {frames.length} frame{frames.length === 1 ? "" : "s"}
            {selectedLayer ? (
              <span className="ml-2 inline-flex items-center gap-1 rounded border border-border bg-background px-1.5 py-0.5 text-[11px] font-medium text-foreground">
                <span>Filtered by layer:</span>
                <span className="font-mono">{selectedLayer.name}</span>
                <button
                  type="button"
                  onClick={() => handleLayerClick(selectedLayer)}
                  className="ml-0.5 rounded text-muted-foreground hover:text-foreground"
                  aria-label="Clear layer filter"
                  title="Clear layer filter"
                >
                  <X className="h-3 w-3" aria-hidden="true" />
                </button>
              </span>
            ) : null}
          </p>
        </div>
        <div>
          <button
            type="button"
            onClick={toggleGraph}
            className="inline-flex items-center gap-1 rounded border border-border bg-background px-2 py-1 text-xs font-medium text-foreground hover:bg-accent"
            aria-pressed={showGraph}
            aria-controls="job-dependency-graph-panel"
            title={showGraph ? "Hide the dependency graph" : "Show the dependency graph"}
          >
            {showGraph ? (
              <ChevronDown className="h-3.5 w-3.5" aria-hidden="true" />
            ) : (
              <ChevronRight className="h-3.5 w-3.5" aria-hidden="true" />
            )}
            <span>Dependency Graph</span>
          </button>
        </div>
      </header>

      <div>
        {loadingLayers && layers.length === 0 ? (
          <TableSkeleton rows={3} />
        ) : layers.length === 0 ? (
          <EmptyState
            icon={<Inbox className="h-5 w-5" aria-hidden="true" />}
            title="No layers"
            description="This job has not reported any layers yet."
            className="py-6"
          />
        ) : (
          <SimpleDataTable
            data={layers}
            columns={layerColumns}
            username={username}
            columnVisibilityStorageKey="cueweb.layers.columnVisibility"
            viewsPageKey="layers"
            onRowClick={handleLayerClick}
            selectedRowId={selectedLayer?.id ?? null}
            toolbarLeft={
              <span className="text-xs font-medium text-muted-foreground">
                Layers [Total Count:{" "}
                <span className="font-semibold text-foreground tabular-nums">
                  {layers.length}
                </span>
                ]
              </span>
            }
          />
        )}
      </div>

      {/* Layer right-click dialogs (Reorder, Stagger, Properties, View
          Dependencies, View Processes, Mark done / Eat and Mark done, and
          the Dependency Wizard). Event-driven, so one mount serves the whole
          layers table. */}
      <LayerExtraDialogs job={job} />

      {(() => {
        const visibleFrames = selectedLayer
          ? frames.filter((f) => f.layerName === selectedLayer.name)
          : frames;
        const framesTitle = (
          <span className="text-xs font-medium text-muted-foreground">
            Frames [Total Count:{" "}
            <span className="font-semibold text-foreground tabular-nums">
              {visibleFrames.length}
            </span>
            {selectedLayer && visibleFrames.length !== frames.length ? (
              <span className="ml-1 text-muted-foreground">of {frames.length}</span>
            ) : null}
            ]
          </span>
        );
        return (
          <div>
            {loadingFrames && frames.length === 0 ? (
              <TableSkeleton rows={6} />
            ) : visibleFrames.length === 0 ? (
              <EmptyState
                icon={<Inbox className="h-5 w-5" aria-hidden="true" />}
                title="No frames"
                description={
                  selectedLayer
                    ? `Layer "${selectedLayer.name}" has not produced any frames yet.`
                    : "This job has not produced any frames yet."
                }
                className="py-6"
              />
            ) : (
              <>
                <FrameRangeSelector frames={visibleFrames} job={job} username={username} />
                <SimpleDataTable
                  data={visibleFrames}
                  columns={frameColumns}
                  username={username}
                  job={job}
                  isFramesTable
                  // Single-click loads the frame into the Attributes panel
                  // (double-click still opens the log viewer). SimpleDataTable
                  // passes row.original (a Frame), so the handler takes it directly.
                  onRowClick={handleFrameClick}
                  selectedRowId={selectedFrame?.id ?? null}
                  columnVisibilityStorageKey="cueweb.frames.columnVisibility"
                  viewsPageKey="frames"
                  // Hide the Remain column (needs the ETA predictor that's only
                  // in CueGUI). Last Line stays visible for CueGUI parity even
                  // though the log-tail fetch isn't wired in yet -> it renders
                  // an em-dash placeholder.
                  defaultColumnVisibility={{ remain: false }}
                  toolbarLeft={framesTitle}
                />
              </>
            )}
          </div>
        );
      })()}

      {/* Frame right-click dialogs (View Dependencies, Reorder, Preview All,
          View Processes, Drop depends / Mark as waiting / Mark done / Eat and
          Mark done, and the Dependency Wizard). Event-driven, one mount. */}
      <FrameExtraDialogs job={job} />
      {/* Frame thumbnail preview slide-over. */}
      <FramePreviewPanel job={job} />

      {showGraph ? (
        <div
          id="job-dependency-graph-panel"
          className="rounded-md border border-border bg-background"
        >
          <div className="flex items-center justify-between border-b border-border px-3 py-2">
            <span className="text-xs font-medium text-muted-foreground">
              Dependency Graph for{" "}
              <span className="font-mono text-foreground">{job.name}</span>
            </span>
            <button
              type="button"
              onClick={toggleGraph}
              className="rounded text-muted-foreground hover:text-foreground"
              aria-label="Hide the dependency graph"
              title="Hide the dependency graph"
            >
              <X className="h-3.5 w-3.5" aria-hidden="true" />
            </button>
          </div>
          <JobDependencyGraph job={job} />
        </div>
      ) : null}
    </section>
  );
}

function TableSkeleton({ rows }: { rows: number }) {
  return (
    <div className="space-y-1.5 rounded-md border border-border p-2">
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} className="h-6 w-full" />
      ))}
    </div>
  );
}
