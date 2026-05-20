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
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { Inbox } from "lucide-react";
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

  // Clear stale rows when the parent selects a different job so the
  // previous job's data doesn't briefly flash in the new context.
  React.useEffect(() => {
    setLayers([]);
    setFrames([]);
  }, [job?.id]);

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
          </p>
        </div>
      </header>

      <div>
        <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Layers
        </h3>
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
            showPagination={false}
          />
        )}
      </div>

      <div>
        <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Frames
        </h3>
        {loadingFrames && frames.length === 0 ? (
          <TableSkeleton rows={6} />
        ) : frames.length === 0 ? (
          <EmptyState
            icon={<Inbox className="h-5 w-5" aria-hidden="true" />}
            title="No frames"
            description="This job has not produced any frames yet."
            className="py-6"
          />
        ) : (
          <SimpleDataTable
            data={frames}
            columns={frameColumns}
            username={username}
            job={job}
            isFramesTable
          />
        )}
      </div>
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
