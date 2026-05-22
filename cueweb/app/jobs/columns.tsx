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


import { ColumnDef } from "@tanstack/react-table";
import { Button } from "@/components/ui/button";
import { ArrowUpDown, MoreHorizontal, StickyNote } from "lucide-react";
import { Checkbox } from "@/components/ui/checkbox";
import { convertMemoryToString, convertUnixToHumanReadableDate, secondsToHHHMM, secondsToHumanAge } from "@/app/utils/layers_frames_utils";
import { Status } from "@/components/ui/status";
import { SubscribeBell } from "@/components/ui/subscribe-bell";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";

// This type is used to define the shape of our data.
// You can use a Zod schema here if you want.
export type JobStats = {
  avgCoreSec: number;
  avgFrameSec: number;
  deadFrames: number;
  dependFrames: number;
  eatenFrames: number;
  failedCoreSec: string;
  failedFrameCount: string;
  failedGpuSec: string;
  highFrameSec: number;
  maxGpuMemory: string;
  maxRss: string;
  pendingFrames: number;
  remainingCoreSec: string;
  renderedCoreSec: string;
  renderedFrameCount: string;
  renderedGpuSec: string;
  reservedCores: number;
  reservedGpus: number;
  runningFrames: number;
  succeededFrames: number;
  totalCoreSec: string;
  totalFrames: number;
  totalGpuSec: string;
  totalLayers: number;
  waitingFrames: number;
};

export type Job = {
  autoEat: boolean;
  facility: string;
  group: string;
  hasComment: boolean;
  id: string;
  isPaused: boolean;
  jobStats: JobStats;
  logDir: string;
  maxCores: number;
  maxGpus: number;
  minCores: number;
  minGpus: number;
  name: string;
  os: string;
  priority: number;
  shot: string;
  show: string;
  startTime: number;
  state: string;
  stopTime: number;
  uid: number;
  user: string;
};

export const getState = (job: Job) => {
  // a job's state is either Paused, Failing, Finished, Dependency, or In Progress
  // cuegui.cuigui.JobMonitorTree.displayStates contains the logic for displaying the correct job state
  if (job?.state === "FINISHED") {
    return "Finished";
  }
  if (job?.isPaused) {
    return "Paused";
  }
  if (job?.jobStats.deadFrames > 0) {
    return "Failing";
  }
  if (
    job?.jobStats.dependFrames &&
    job?.jobStats.dependFrames === job?.jobStats.pendingFrames &&
    job?.jobStats.runningFrames === 0
  ) {
    return "Dependency";
  }
  return "In Progress";
};

// given a job name, will return the part of the name that contains the show, shot, user
export const getShowShotUser = (jobName: string) => {
  const showShotUser = jobName.split("_")[0];
  return showShotUser;
};

// given a job name, will return the part of the name that comes after show, shot, user
export const getRestOfJobName = (jobName: string) => {
  const restOfName = jobName.replace(`${getShowShotUser(jobName)}_`, "");
  return restOfName;
};

export const getJobAge = (job: Job) => {
  if (job?.stopTime != 0) {
    return secondsToHHHMM(job.stopTime - job.startTime);
  }
  const currentDate = new Date();
  const timestampInSeconds = currentDate.getTime() / 1000;
  return secondsToHHHMM(timestampInSeconds - job.startTime);
};

export const getJobAgeInSeconds = (job: Job): number => {
  if (job?.stopTime != 0) {
    return Math.max(0, Math.floor(job.stopTime - job.startTime));
  }
  const nowInSeconds = Math.floor(Date.now() / 1000);
  return Math.max(0, nowInSeconds - Math.floor(job.startTime));
};

export const getJobReadableAge = (job: Job) => {
  return secondsToHumanAge(getJobAgeInSeconds(job));
};

// Sticky-note icon shown next to jobs that have one or more comments
// (mirrors the comment indicator column in cuegui.JobMonitorTree).
function JobCommentIndicator({ job, username }: { job: Job; username?: string }) {
  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    const params = new URLSearchParams({ jobId: job.id });
    if (username) params.set("username", username);
    const url = `/jobs/${encodeURIComponent(job.name)}/comments?${params.toString()}`;
    window.open(url, "_blank", "noopener,noreferrer");
  };
  return (
    <TooltipProvider delayDuration={200}>
      <Tooltip>
        <TooltipTrigger asChild>
          <button
            type="button"
            onClick={handleClick}
            aria-label="View comments"
            className="inline-flex items-center justify-center text-amber-500 hover:text-amber-400"
          >
            <StickyNote className="h-4 w-4" />
          </button>
        </TooltipTrigger>
        <TooltipContent>Has comments — click to view</TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

export const columns: ColumnDef<Job>[] = [
  // accessorKey is the unique id for each column, header is the string that shows as the header in the row
  {
    id: "select",
    header: ({ table }) => (
      <Checkbox
        checked={table.getIsAllPageRowsSelected() || (table.getIsSomePageRowsSelected() && "indeterminate")}
        onCheckedChange={(value) => table.toggleAllPageRowsSelected(!!value)}
        aria-label="Select all"
      />
    ),
    cell: ({ row }) => (
      <Checkbox
        checked={row.getIsSelected()}
        onCheckedChange={(value) => row.toggleSelected(!!value)}
        aria-label="Select row"
      />
    ),
    enableSorting: false,
    enableHiding: false,
  },
  {
    accessorKey: "name",
    header: ({ column }) => {
      return (
        <Button variant="ghost" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
          Name
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      );
    },
    // A job name has the format `${show-shot-user}_${jobName}_[optional suffix]`
    // The next few lines split up the job name into two lines for easier readability
    // One line for show/show/user and another for the rest of the job name
    cell: ({ row, table }) => {
      const job = row.original as Job;
      const username = (table.options.meta as { username?: string } | undefined)?.username;
      return (
        <>
          <div className="flex items-center gap-1">
            <span>{getShowShotUser(job.name)}</span>
            {job.hasComment && <JobCommentIndicator job={job} username={username} />}
          </div>
          <div>{getRestOfJobName(job.name)}</div>
        </>
      );
    },
  },
  {
    accessorKey: "state",
    header: ({ column }) => {
      return (
        <Button variant="ghost" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
          State
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      );
    },
    cell: ({ row }) => <Status status={getState(row.original as Job)} />,
    sortingFn: (rowA, rowB) => {
      const stateA = getState(rowA.original as Job);
      const stateB = getState(rowB.original as Job);
      const stateOrder = {
        "Failing": 0,
        "Finished": 1,
        "In Progress": 2,
        "Dependency": 3,
        "Paused": 4,
      };

      return (stateOrder[stateA] || 5) - (stateOrder[stateB] || 5);
    },
  },
  {
    id: "done / total",
    accessorFn: (row) => `${row.jobStats.succeededFrames} of ${row.jobStats.totalFrames}`,
    header: ({ column }) => {
      return (
        <Button variant="ghost" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
          Done / Total
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      );
    },
  },
  {
    id: "started",
    accessorFn: (row) => convertUnixToHumanReadableDate(row.startTime),
    header: ({ column }) => {
      return (
        <Button variant="ghost" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
          Started
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      );
    },
  },
  {
    id: "finished",
    accessorFn: (row) => convertUnixToHumanReadableDate(row.stopTime),
    header: ({ column }) => {
      return (
        <Button variant="ghost" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
          Finished
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      );
    },
  },
  {
    id: "running",
    accessorFn: (row) => row.jobStats.runningFrames,
    header: ({ column }) => {
      return (
        <Button variant="ghost" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
          Running
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      );
    },
  },
  {
    id: "dead",
    accessorFn: (row) => row.jobStats.deadFrames,
    header: ({ column }) => {
      return (
        <Button variant="ghost" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
          Dead
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      );
    },
  },
  {
    id: "eaten",
    accessorFn: (row) => row.jobStats.eatenFrames,
    header: ({ column }) => {
      return (
        <Button variant="ghost" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
          Eaten
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      );
    },
  },
  {
    id: "wait",
    accessorFn: (row) => row.jobStats.waitingFrames,
    header: ({ column }) => {
      return (
        <Button variant="ghost" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
          Wait
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      );
    },
  },
  {
    id: "maxRss",
    accessorFn: (row) => convertMemoryToString(Number.parseInt(row.jobStats.maxRss), JSON.stringify(row)),
    header: ({ column }) => {
      return (
        <Button variant="ghost" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
          MaxRss
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      );
    },
  },
  {
    id: "age",
    accessorFn: (row) => getJobAge(row),
    header: ({ column }) => {
      return (
        <Button variant="ghost" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
          Age
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      );
    },
  },
  {
    id: "readable age",
    accessorFn: (row) => getJobReadableAge(row),
    header: ({ column }) => {
      return (
        <Button variant="ghost" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
          Readable Age
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      );
    },
    sortingFn: (rowA, rowB) => {
      const ageA = getJobAgeInSeconds(rowA.original as Job);
      const ageB = getJobAgeInSeconds(rowB.original as Job);
      return ageA - ageB;
    },
  },
  {
    accessorKey: "progress",
    header: "Progress",
  },
  {
    id: "subscribe",
    header: () => null,
    cell: ({ row }) => (
      <SubscribeBell
        jobId={(row.original as Job).id}
        jobName={(row.original as Job).name}
        jobState={(row.original as Job).state}
      />
    ),
    enableSorting: false,
    enableHiding: false,
  },
  {
    id: "pop-up",
    header: "",
    enableHiding: false,
  },
];
