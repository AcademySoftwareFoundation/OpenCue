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
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { Inbox, X } from "lucide-react";
import { FramesLayersPopup } from "./frames-layers-popup";
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

  React.useEffect(() => {
    if (!job) return;

    let cancelled = false;

    const load = async (initial: boolean) => {
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
          <FramesLayersPopup job={job} username={username} />
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
              <SimpleDataTable
                data={visibleFrames}
                columns={frameColumns}
                username={username}
                job={job}
                isFramesTable
                columnVisibilityStorageKey="cueweb.frames.columnVisibility"
                // Hide the Remain column (needs the ETA predictor that's only
                // in CueGUI). Last Line stays visible for CueGUI parity even
                // though the log-tail fetch isn't wired in yet -> it renders
                // an em-dash placeholder.
                defaultColumnVisibility={{ remain: false }}
                toolbarLeft={framesTitle}
              />
            )}
          </div>
        );
      })()}
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
