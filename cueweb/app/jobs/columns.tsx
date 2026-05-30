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
import { ColumnDef } from "@tanstack/react-table";
import { Button } from "@/components/ui/button";
import { ArrowUpDown, MoreHorizontal, StickyNote, X } from "lucide-react";
import { Checkbox } from "@/components/ui/checkbox";
import { convertMemoryToString, convertUnixToHumanReadableDate, secondsToHHHMM, secondsToHumanAge } from "@/app/utils/layers_frames_utils";
import { RowActionsCell } from "@/components/ui/row-actions-cell";
import { FramesLayersPopup } from "@/components/ui/frames-layers-popup";
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
  eligibleTime?: number;
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

// Per-job color swatch backed by localStorage (key: cueweb.userColors,
// map of jobId -> hex). Matches CueGUI's User Color column: a small
// clickable square that opens the native color picker; right-click clears.
// Cross-tab updates ride the standard `storage` event.
const USER_COLORS_KEY = "cueweb.userColors";

function readUserColors(): Record<string, string> {
  if (typeof window === "undefined") return {};
  try {
    const raw = window.localStorage.getItem(USER_COLORS_KEY);
    return raw ? (JSON.parse(raw) as Record<string, string>) : {};
  } catch {
    return {};
  }
}

function writeUserColors(map: Record<string, string>): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(USER_COLORS_KEY, JSON.stringify(map));
    // Notify same-tab listeners; the browser's `storage` event only fires
    // on OTHER tabs by default.
    window.dispatchEvent(new CustomEvent("cueweb:user-colors"));
  } catch {
    // Quota / private mode; silently ignore.
  }
}

function UserColorSwatch({ jobId }: { jobId: string }) {
  const [colors, setColors] = React.useState<Record<string, string>>({});
  const inputRef = React.useRef<HTMLInputElement | null>(null);

  React.useEffect(() => {
    setColors(readUserColors());
    const refresh = () => setColors(readUserColors());
    window.addEventListener("storage", refresh);
    window.addEventListener("cueweb:user-colors", refresh);
    return () => {
      window.removeEventListener("storage", refresh);
      window.removeEventListener("cueweb:user-colors", refresh);
    };
  }, []);

  const current = colors[jobId] || "";

  const onChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const next = e.target.value;
    const map = { ...readUserColors(), [jobId]: next };
    writeUserColors(map);
  };

  const clear = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    const map = { ...readUserColors() };
    delete map[jobId];
    writeUserColors(map);
  };

  return (
    <span className="inline-flex items-center gap-1">
      <input
        ref={inputRef}
        type="color"
        value={current || "#888888"}
        onChange={onChange}
        aria-label="Set user color"
        title={current ? `User color: ${current} (right-click to clear)` : "Click to set a user color"}
        onContextMenu={current ? clear : undefined}
        className={`h-4 w-4 cursor-pointer rounded-sm border border-border bg-transparent p-0 ${current ? "" : "opacity-60"}`}
        style={current ? { backgroundColor: current } : undefined}
      />
      {current ? (
        <button
          type="button"
          onClick={clear}
          aria-label="Clear user color"
          title="Clear user color"
          className="text-muted-foreground hover:text-foreground"
        >
          <X className="h-3 w-3" aria-hidden="true" />
        </button>
      ) : null}
    </span>
  );
}

// Sticky-note icon shown next to jobs that have one or more comments
// (mirrors the comment indicator column in cuegui.JobMonitorTree).
function JobCommentIndicator({ job }: { job: Job }) {
  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    const params = new URLSearchParams({ jobId: job.id });
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
    // Mobile-friendly equivalent of right-click. Stays in column 2 so the
    // button is always one tap away even when the table scrolls
    // horizontally.
    id: "actions",
    header: () => <span className="sr-only">Actions</span>,
    cell: ({ row, table }) => (
      <RowActionsCell row={row} table={table} label="Open job actions" />
    ),
    enableSorting: false,
    enableHiding: false,
  },
  {
    accessorKey: "name",
    header: ({ column }) => {
      return (
        <Button variant="ghost" size="sm" className="-mx-2 h-7 px-1.5 text-xs font-medium" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
          Name
          <ArrowUpDown className="ml-1 h-3 w-3 opacity-60" />
        </Button>
      );
    },
    // A job name has the format `${show-shot-user}_${jobName}_[optional suffix]`
    // The next few lines split up the job name into two lines for easier readability
    // One line for show/show/user and another for the rest of the job name.
    // The sticky-note comment indicator used to render inline next to the
    // first line; it's now a dedicated `comments` column to the right so
    // the user can sort jobs by "has a comment" the way CueGUI does.
    cell: ({ row }) => {
      const job = row.original as Job;
      return (
        <div className="mx-auto max-w-[200px] text-center" title={job.name}>
          <div className="truncate">{getShowShotUser(job.name)}</div>
          <div className="truncate">{getRestOfJobName(job.name)}</div>
        </div>
      );
    },
  },
  {
    // Dedicated comments column. Sortable so users can pull jobs with
    // comments to the top (CueGUI parity: cuegui.JobMonitorTree renders
    // a tiny note-icon column right next to the job name).
    id: "comments",
    accessorFn: (row) => (row.hasComment ? 1 : 0),
    header: ({ column }) => (
      <Button
        variant="ghost"
        size="sm"
        className="-mx-2 h-7 px-1.5 text-xs font-medium"
        onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
        title="Sort by jobs with comments"
      >
        <StickyNote className="h-3.5 w-3.5" aria-hidden="true" />
        <ArrowUpDown className="ml-1 h-3 w-3 opacity-60" />
        <span className="sr-only">Comments</span>
      </Button>
    ),
    cell: ({ row }) => {
      const job = row.original as Job;
      if (!job.hasComment) return null;
      return <JobCommentIndicator job={job} />;
    },
    sortingFn: (rowA, rowB) => {
      const a = (rowA.original as Job).hasComment ? 1 : 0;
      const b = (rowB.original as Job).hasComment ? 1 : 0;
      return a - b;
    },
  },
  {
    accessorKey: "state",
    header: ({ column }) => {
      return (
        <Button variant="ghost" size="sm" className="-mx-2 h-7 px-1.5 text-xs font-medium" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
          State
          <ArrowUpDown className="ml-1 h-3 w-3 opacity-60" />
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
        <Button variant="ghost" size="sm" className="-mx-2 h-7 px-1.5 text-xs font-medium" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
          Done / Total
          <ArrowUpDown className="ml-1 h-3 w-3 opacity-60" />
        </Button>
      );
    },
  },
  {
    id: "running",
    accessorFn: (row) => row.jobStats.runningFrames,
    header: ({ column }) => {
      return (
        <Button variant="ghost" size="sm" className="-mx-2 h-7 px-1.5 text-xs font-medium" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
          Running
          <ArrowUpDown className="ml-1 h-3 w-3 opacity-60" />
        </Button>
      );
    },
  },
  {
    id: "dead",
    accessorFn: (row) => row.jobStats.deadFrames,
    header: ({ column }) => {
      return (
        <Button variant="ghost" size="sm" className="-mx-2 h-7 px-1.5 text-xs font-medium" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
          Dead
          <ArrowUpDown className="ml-1 h-3 w-3 opacity-60" />
        </Button>
      );
    },
  },
  {
    id: "eaten",
    accessorFn: (row) => row.jobStats.eatenFrames,
    header: ({ column }) => {
      return (
        <Button variant="ghost" size="sm" className="-mx-2 h-7 px-1.5 text-xs font-medium" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
          Eaten
          <ArrowUpDown className="ml-1 h-3 w-3 opacity-60" />
        </Button>
      );
    },
  },
  {
    id: "wait",
    accessorFn: (row) => row.jobStats.waitingFrames,
    header: ({ column }) => {
      return (
        <Button variant="ghost" size="sm" className="-mx-2 h-7 px-1.5 text-xs font-medium" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
          Wait
          <ArrowUpDown className="ml-1 h-3 w-3 opacity-60" />
        </Button>
      );
    },
  },
  {
    id: "maxRss",
    accessorFn: (row) => convertMemoryToString(Number.parseInt(row.jobStats.maxRss), JSON.stringify(row)),
    header: ({ column }) => {
      return (
        <Button variant="ghost" size="sm" className="-mx-2 h-7 px-1.5 text-xs font-medium" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
          MaxRss
          <ArrowUpDown className="ml-1 h-3 w-3 opacity-60" />
        </Button>
      );
    },
  },
  {
    id: "age",
    accessorFn: (row) => getJobAge(row),
    header: ({ column }) => {
      return (
        <Button variant="ghost" size="sm" className="-mx-2 h-7 px-1.5 text-xs font-medium" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
          Age
          <ArrowUpDown className="ml-1 h-3 w-3 opacity-60" />
        </Button>
      );
    },
  },
  {
    id: "readable age",
    accessorFn: (row) => getJobReadableAge(row),
    header: ({ column }) => {
      return (
        <Button variant="ghost" size="sm" className="-mx-2 h-7 px-1.5 text-xs font-medium" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
          Readable Age
          <ArrowUpDown className="ml-1 h-3 w-3 opacity-60" />
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
    // Column id kept as "started" so existing localStorage visibility
    // entries don't get orphaned by the relabel. Header text matches the
    // CueGUI "Launched" column.
    id: "started",
    accessorFn: (row) => convertUnixToHumanReadableDate(row.startTime),
    header: ({ column }) => {
      return (
        <Button variant="ghost" size="sm" className="-mx-2 h-7 px-1.5 text-xs font-medium" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
          Launched
          <ArrowUpDown className="ml-1 h-3 w-3 opacity-60" />
        </Button>
      );
    },
  },
  {
    id: "eligible",
    accessorFn: (row) => (row.eligibleTime ? convertUnixToHumanReadableDate(row.eligibleTime) : ""),
    header: ({ column }) => {
      return (
        <Button variant="ghost" size="sm" className="-mx-2 h-7 px-1.5 text-xs font-medium" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
          Eligible
          <ArrowUpDown className="ml-1 h-3 w-3 opacity-60" />
        </Button>
      );
    },
  },
  {
    id: "finished",
    accessorFn: (row) => convertUnixToHumanReadableDate(row.stopTime),
    header: ({ column }) => {
      return (
        <Button variant="ghost" size="sm" className="-mx-2 h-7 px-1.5 text-xs font-medium" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
          Finished
          <ArrowUpDown className="ml-1 h-3 w-3 opacity-60" />
        </Button>
      );
    },
  },
  {
    id: "user color",
    header: () => (
      <span title="Per-job color marker (persisted locally)" className="cursor-help">
        User Color
      </span>
    ),
    cell: ({ row }) => <UserColorSwatch jobId={(row.original as Job).id} />,
    enableSorting: false,
  },
  {
    accessorKey: "progress",
    header: "Progress",
  },
  {
    id: "notify",
    // Short column label so users know the bell column exists and what
    // it does. Hover tooltip on the title explains the feature; the bell
    // button itself carries its own per-row tooltip describing the
    // current subscription state. Listed in the Columns dropdown so the
    // user can hide it if they don't use the notification feature.
    header: () => (
      <span
        title="Subscribe to a desktop / in-app notification when this job finishes"
        className="cursor-help"
      >
        Notify
      </span>
    ),
    cell: ({ row }) => (
      <SubscribeBell
        jobId={(row.original as Job).id}
        jobName={(row.original as Job).name}
        jobState={(row.original as Job).state}
      />
    ),
    enableSorting: false,
  },
];
