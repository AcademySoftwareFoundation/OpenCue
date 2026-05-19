"use client";

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
