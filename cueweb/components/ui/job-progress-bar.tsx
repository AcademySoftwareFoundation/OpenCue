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


import { Job } from "@/app/jobs/columns";
import {
  getJobProgressSegments,
  getJobProgressTooltipRows,
} from "@/app/utils/job_progress_utils";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import ProgressBar from "./progressbar";

type JobProgressBarProps = {
  job: Job;
};

export function JobProgressBar({ job }: JobProgressBarProps) {
  const progressSegments = getJobProgressSegments(job);
  const tooltipRows = getJobProgressTooltipRows(job);

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <div>
            <ProgressBar visualParts={progressSegments} />
          </div>
        </TooltipTrigger>
        <TooltipContent>
          <div className="grid grid-cols-[auto_auto_auto] gap-x-3 gap-y-1">
            {tooltipRows.map((row) => (
              <div className="contents" key={row.label}>
                <span>{row.label}</span>
                <span className="text-right">{row.count}</span>
                <span className="text-right">{row.percentage}</span>
              </div>
            ))}
          </div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
