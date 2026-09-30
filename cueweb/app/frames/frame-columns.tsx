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
import { ArrowUpDown, Image as ImageIcon } from "lucide-react";
import { convertUnixToHumanReadableDate, convertMemoryToString, secondsToHHMMSS } from "@/app/utils/layers_frames_utils";
import { RowActionsCell } from "@/components/ui/row-actions-cell";

export type Frame = {
  id: string;
  name: string;
  layerName: string;
  number: number;
  state: string;
  retryCount: number;
  exitStatus: number;
  dispatchOrder: number;
  startTime: number;
  stopTime: number;
  maxRss: string;
  usedMemory: string;
  reservedMemory: string;
  reservedGpuMemory: string;
  lastResource: string;
  checkpointState: string;
  checkpointCount: number;
  totalCoreTime: number;
  lluTime: number;
  totalGpuTime: number;
  maxGpuMemory: string;
  usedGpuMemory: string;
  frameStateDisplayOverride: string;
  maxPss?: string;
  usedPss?: string;
  eligibleTime?: number;
  submissionTime?: number;
};

const getFrameCores = (frame: Frame) => {
  const parts = frame.lastResource.split("/");
  return parts.length > 1 ? parts[1] : "N/A";
};

const getFrameGpus = (frame: Frame) => {
  const parts = frame.lastResource.split("/");
  return parts.length > 2 ? parts[2] : "N/A";
};

const getFrameMemory = (frame: Frame) => {
  const memory = frame.state === "RUNNING" ? frame.usedMemory : frame.maxRss;
  return memory ? convertMemoryToString(parseInt(memory), JSON.stringify(frame)) : "N/A";
};

// Mirrors getFrameMemory but reads PSS (proportional set size) - while a
// frame is running, used_pss is the live value; once stopped, max_pss is
// the high-water mark CueGUI displays.
const getFramePss = (frame: Frame) => {
  const pss = frame.state === "RUNNING" ? frame.usedPss : frame.maxPss;
  return pss ? convertMemoryToString(parseInt(pss), JSON.stringify(frame)) : "N/A";
};

// CueGUI's LLU column shows the elapsed time since the frame's log was
// last updated. It's only meaningful while a frame is actively running:
// for WAITING / DEPEND / SUCCEEDED / DEAD frames there's no live log, so
// CueGUI leaves the cell blank and we mirror that here. (Cuebot may
// surface a non-zero llu_time on frames that already finished, which
// caused the prior implementation to render a garbage "time since" value
// for every paused / waiting frame.)
const getFrameLLU = (frame: Frame, nowSeconds: number) => {
  if (frame.state !== "RUNNING") return "";
  if (!frame.lluTime) return "";
  const delta = nowSeconds - frame.lluTime;
  if (delta < 0) return "";
  return secondsToHHMMSS(delta);
};

const getFrameGpuMemory = (frame: Frame) => {
  const gpuMemory = frame.state === "RUNNING" ? frame.usedGpuMemory : frame.maxGpuMemory;
  return gpuMemory ? convertMemoryToString(parseInt(gpuMemory), JSON.stringify(frame)) : "N/A";
};

const getFrameRuntime = (frame: Frame, currentTimestampInSeconds: number) => {
  if (frame.stopTime !== 0) {
    return secondsToHHMMSS(frame.stopTime - frame.startTime);
  }
  if (frame.startTime !== 0) {
    return secondsToHHMMSS(currentTimestampInSeconds - frame.startTime);
  }
  return "00:00:00";
};

const SortingButton = ({ column, label }: { column: any; label: string }) => (
  <Button variant="ghost" className="px-1 py-1 mx-0" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
    {label}
    <ArrowUpDown className="ml-1 h-4 w-3" />
  </Button>
);

export const frameColumns: ColumnDef<Frame>[] = [
  {
    // Mobile-friendly equivalent of right-click. Sits at the leftmost
    // edge of the row so the trigger is always reachable.
    id: "actions",
    header: () => <span className="sr-only">Actions</span>,
    cell: ({ row, table }) => (
      <RowActionsCell row={row} table={table} label="Open frame actions" />
    ),
    enableSorting: false,
    enableHiding: false,
  },
  {
    // Frame preview thumbnail: opens the rendered image in a right-side
    // slide-over (FramePreviewPanel). The panel resolves the output path from
    // the frame's layer, so the per-row trigger only needs the frame.
    id: "preview",
    header: () => <span className="sr-only">Preview</span>,
    cell: ({ row }) => (
      <Button
        variant="ghost"
        size="icon"
        className="h-7 w-7"
        aria-label="Preview frame"
        title="Preview rendered frame"
        onClick={(e) => {
          e.stopPropagation();
          window.dispatchEvent(
            new CustomEvent("cueweb:open-frame-thumbnail", { detail: { frame: row.original } }),
          );
        }}
      >
        <ImageIcon className="h-4 w-4" aria-hidden="true" />
      </Button>
    ),
    enableSorting: false,
    enableHiding: true,
  },
  {
    accessorKey: "dispatchOrder",
    header: ({ column }) => <SortingButton column={column} label="Order" />,
  },
  {
    accessorKey: "number",
    header: ({ column }) => <SortingButton column={column} label="Frame" />,
  },
  {
    accessorKey: "layerName",
    header: ({ column }) => <SortingButton column={column} label="Layer" />,
  },
  {
    accessorKey: "state",
    header: ({ column }) => <SortingButton column={column} label="Status" />,
  },
  {
    accessorKey: "cores",
    header: ({ column }) => <SortingButton column={column} label="Cores" />,
    cell: ({ row }) => getFrameCores(row.original),
  },
  {
    accessorKey: "gpus",
    header: ({ column }) => <SortingButton column={column} label="GPUs" />,
    cell: ({ row }) => getFrameGpus(row.original),
  },
  {
    accessorKey: "lastResource",
    header: ({ column }) => <SortingButton column={column} label="Host" />,
  },
  {
    accessorKey: "retryCount",
    header: ({ column }) => <SortingButton column={column} label="Retries" />,
  },
  {
    accessorKey: "checkpointCount",
    header: ({ column }) => <SortingButton column={column} label="CheckP" />,
  },
  {
    id: "runtime",
    accessorFn: (row) => getFrameRuntime(row, new Date().getTime() / 1000),
    header: ({ column }) => <SortingButton column={column} label="Runtime" />,
  },
  {
    id: "llu",
    accessorFn: (row) => getFrameLLU(row, new Date().getTime() / 1000),
    header: ({ column }) => <SortingButton column={column} label="LLU" />,
  },
  {
    // Kept the accessorKey so existing localStorage visibility entries
    // ("usedMemory") still match. Label changed to match CueGUI parity.
    accessorKey: "usedMemory",
    header: ({ column }) => <SortingButton column={column} label="Memory (RSS)" />,
    cell: ({ row }) => getFrameMemory(row.original),
  },
  {
    id: "memoryPss",
    accessorFn: (row) => getFramePss(row),
    header: ({ column }) => <SortingButton column={column} label="Memory (PSS)" />,
  },
  {
    accessorKey: "usedGpuMemory",
    header: ({ column }) => <SortingButton column={column} label="GPU Memory" />,
    cell: ({ row }) => getFrameGpuMemory(row.original),
  },
  {
    // CueGUI's "Remain" is fed by FrameEtaDataBuffer (a backend predictor
    // not yet wired into CueWeb). Render an em-dash placeholder for now so
    // users can still toggle the column on/off via the Columns dropdown.
    id: "remain",
    accessorFn: () => "—",
    header: ({ column }) => <SortingButton column={column} label="Remain" />,
    enableSorting: false,
  },
  {
    accessorKey: "startTime",
    header: ({ column }) => <SortingButton column={column} label="Start Time" />,
    cell: ({ row }) => convertUnixToHumanReadableDate(row.original.startTime),
  },
  {
    accessorKey: "stopTime",
    header: ({ column }) => <SortingButton column={column} label="Stop Time" />,
    cell: ({ row }) => convertUnixToHumanReadableDate(row.original.stopTime),
  },
  {
    id: "eligibleTime",
    accessorFn: (row) => (row.eligibleTime ? convertUnixToHumanReadableDate(row.eligibleTime) : ""),
    header: ({ column }) => <SortingButton column={column} label="Eligible Time" />,
  },
  {
    id: "submissionTime",
    accessorFn: (row) => (row.submissionTime ? convertUnixToHumanReadableDate(row.submissionTime) : ""),
    header: ({ column }) => <SortingButton column={column} label="Submission Time" />,
  },
  {
    // CueGUI's "Last Line" requires an async log-tail fetch per frame; not
    // yet wired into the REST gateway. Render a placeholder so the column
    // shows up in the Columns dropdown for visual parity.
    id: "lastLine",
    accessorFn: () => "—",
    header: ({ column }) => <SortingButton column={column} label="Last Line" />,
    enableSorting: false,
  },
];
