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

import { memo, useMemo } from "react";
import Link from "next/link";
import { useDraggable } from "@dnd-kit/react";
import { Briefcase, GripVertical } from "lucide-react";
import type { Job } from "@/app/jobs/columns";
import { getJobStateDotColor, getState } from "@/app/utils/job_state";
import { getJobProgressSegments, getJobProgressTooltipRows } from "@/app/utils/job_progress_utils";

const INDENT_PER_LEVEL_REM = 1.25;
const BASE_PADDING_REM = 0.25;

type Props = {
  job: Job;
  depth: number;
  fromGroupId: string;
};

function JobLeafBase({ job, depth, fromGroupId }: Props) {
  const dragData = useMemo(
    () => ({ type: "job" as const, name: job.name, fromGroupId }),
    [job.name, fromGroupId],
  );

  const { ref: dragRef, handleRef, isDragSource } = useDraggable({
    id: job.id,
    data: dragData,
  });

  const paddingLeft = `${BASE_PADDING_REM + depth * INDENT_PER_LEVEL_REM}rem`;
  const rowStyle: React.CSSProperties = {
    paddingLeft,
    visibility: isDragSource ? "hidden" : undefined,
  };

  const stateLabel = getState(job);
  const progressSegments = getJobProgressSegments(job);
  const progressTitle = getJobProgressTooltipRows(job)
    .map((row) => `${row.label}: ${row.count} (${row.percentage})`)
    .join("\n");
  const deadFrames = job.jobStats?.deadFrames ?? 0;

  return (
    <div ref={dragRef} className="flex items-center w-full" style={rowStyle}>
      <button
        ref={handleRef}
        type="button"
        aria-label={`Drag job ${job.name}`}
        className="w-6 shrink-0 flex items-center justify-center py-1.5 cursor-grab text-muted-foreground hover:text-foreground"
      >
        <GripVertical className="h-4 w-4" />
      </button>
      <Link
        href={`/jobs/${encodeURIComponent(job.name)}`}
        draggable={false}
        className="flex-1 flex items-center py-1.5 pr-3 hover:bg-muted/50 transition-colors"
      >
        <span className="h-4 w-4 shrink-0" aria-hidden />
        <Briefcase className="h-4 w-4 shrink-0 ml-2 text-muted-foreground" />
        <span className="truncate ml-2">{job.name}</span>
        <span className="ml-auto flex items-center gap-2 shrink-0">
          {deadFrames > 0 && (
            <span className="text-xs text-red-600 dark:text-red-400">{deadFrames} dead</span>
          )}
          <span
            className="h-1.5 w-16 rounded-sm overflow-hidden bg-muted flex"
            title={progressTitle}
            aria-hidden
          >
            {progressSegments.map((segment, i) => (
              <span
                key={i}
                style={{ width: segment.percentage, backgroundColor: segment.color }}
              />
            ))}
          </span>
          <span
            className={`h-2 w-2 rounded-full ${getJobStateDotColor(job)}`}
            title={stateLabel}
            aria-label={stateLabel}
            role="img"
          />
        </span>
      </Link>
    </div>
  );
}

// Memoized so a job row doesn't re-render when an ancestor re-renders mid-drag.
export const JobLeaf = memo(JobLeafBase);
