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
import { ArrowUpDown } from "lucide-react";
import { convertMemoryToString, convertUnixToHumanReadableDate, secondsToHHMMSS, secondsToHHHMM } from "@/app/utils/layers_frames_utils";
import { layerStartAfterSeconds } from "@/app/utils/layer_start_after_utils";
import { LayerProgressBar } from "@/components/ui/layer-progress-bar";
import { RowActionsCell } from "@/components/ui/row-actions-cell";

export type LayerStats = {
  totalFrames: number;
  waitingFrames: number;
  runningFrames: number;
  deadFrames: number;
  eatenFrames: number;
  dependFrames: number;
  succeededFrames: number;
  pendingFrames: number;
  avgFrameSec: number;
  lowFrameSec: number;
  highFrameSec: number;
  avgCoreSec: number;
  renderedFrameCount: string;
  failedFrameCount: string;
  remainingCoreSec: string;
  totalCoreSec: string;
  renderedCoreSec: string;
  failedCoreSec: string;
  maxRss: string;
  reservedCores: number;
  totalGpuSec: string;
  renderedGpuSec: string;
  failedGpuSec: string;
  reservedGpus: number;
  maxGpuMemory: string;
};

export type Layer = {
  id: string;
  name: string;
  range: string;
  tags: string[];
  minCores: number;
  maxCores: number;
  isThreadable: boolean;
  minMemory: string;
  minGpuMemory: string;
  chunkSize: number;
  dispatchOrder: number;
  type: string;
  services: string[];
  memoryOptimizerEnabled: boolean;
  layerStats: LayerStats;
  parentId: string;
  limits: string[];
  timeout: number;
  timeoutLlu: number;
  minGpus: number;
  maxGpus: number;
  eligibleTime?: number;
  // No frame of this layer may start before this time (UTC epoch seconds;
  // 0 / absent = no delay). Declared as `number | string` because the gateway
  // marshals the proto int64 as a JSON string - same as minMemory/maxRss.
  startAfter?: number | string;
  // Free-text provenance for startAfter, e.g. "Set by <user>" or
  // "Automatic backoff: exit status 330". Displayed verbatim.
  startAfterReason?: string;
};

const renderHeader = (title: string, column: any) => (
  <Button variant="ghost" className="px-1 py-1 mx-0" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
    {title}
    <ArrowUpDown className="ml-1 h-4 w-3" />
  </Button>
);

export const layerColumns: ColumnDef<Layer>[] = [
  {
    // Mobile-friendly equivalent of right-click. Sits at the leftmost
    // edge of the row so the trigger is always reachable.
    id: "actions",
    header: () => <span className="sr-only">Actions</span>,
    cell: ({ row, table }) => (
      <RowActionsCell row={row} table={table} label="Open layer actions" />
    ),
    enableSorting: false,
    enableHiding: false,
  },
  {
    accessorKey: "dispatchOrder",
    header: ({ column }) => renderHeader("Dispatch Order", column),
  },
  {
    accessorKey: "name",
    header: ({ column }) => renderHeader("Name", column),
  },
  {
    accessorKey: "services",
    header: ({ column }) => renderHeader("Services", column),
  },
  {
    accessorKey: "limits",
    header: ({ column }) => renderHeader("Limits", column),
  },
  {
    accessorKey: "range",
    header: ({ column }) => renderHeader("Range", column),
  },
  {
    accessorKey: "minCores",
    header: ({ column }) => renderHeader("Cores", column),
  },
  {
    id: "minMemory",
    accessorFn: (row) => convertMemoryToString(Number.parseInt(row.minMemory), JSON.stringify(row)),
    header: ({ column }) => renderHeader("Memory", column),
  },
  {
    accessorKey: "minGpus",
    header: ({ column }) => renderHeader("Gpus", column),
  },
  {
    id: "minGpuMemory",
    accessorFn: (row) => convertMemoryToString(Number.parseInt(row.minGpuMemory), JSON.stringify(row)),
    header: ({ column }) => renderHeader("Gpu Memory", column),
  },
  {
    id: "maxRss",
    accessorFn: (row) => row.layerStats ? convertMemoryToString(Number.parseInt(row.layerStats.maxRss), JSON.stringify(row)) : "N/A",
    header: ({ column }) => renderHeader("MaxRss", column),
  },
  {
    id: "totalFrames",
    accessorFn: (row) => row.layerStats.totalFrames,
    header: ({ column }) => renderHeader("Total", column),
  },
  {
    id: "succeededFrames",
    accessorFn: (row) => row.layerStats.succeededFrames,
    header: ({ column }) => renderHeader("Done", column),
  },
  {
    id: "runningFrames",
    accessorFn: (row) => row.layerStats.runningFrames,
    header: ({ column }) => renderHeader("Run", column),
  },
  {
    id: "dependFrames",
    accessorFn: (row) => row.layerStats.dependFrames,
    header: ({ column }) => renderHeader("Depend", column),
  },
  {
    id: "waitingFrames",
    accessorFn: (row) => row.layerStats.waitingFrames,
    header: ({ column }) => renderHeader("Wait", column),
  },
  {
    id: "eatenFrames",
    accessorFn: (row) => row.layerStats.eatenFrames,
    header: ({ column }) => renderHeader("Eaten", column),
  },
  {
    id: "deadFrames",
    accessorFn: (row) => row.layerStats.deadFrames,
    header: ({ column }) => renderHeader("Dead", column),
  },
  {
    id: "avgFrameSec",
    accessorFn: (row) => secondsToHHMMSS(row.layerStats.avgFrameSec),
    header: ({ column }) => renderHeader("Avg", column),
  },
  {
    accessorKey: "tags",
    header: ({ column }) => renderHeader("Tags", column),
  },
  {
    id: "progress",
    // Keep the numeric percentage as the accessor value so sorting still
    // works on a real number; the cell renders the animated stacked bar
    // (same component the Jobs table uses).
    accessorFn: (row) => {
      if (row.layerStats.totalFrames === 0) return 0;
      return (row.layerStats.succeededFrames / row.layerStats.totalFrames) * 100;
    },
    sortingFn: (rowA, rowB, columnId) => {
      return (rowA.getValue(columnId) as number) - (rowB.getValue(columnId) as number);
    },
    cell: ({ row }) => <LayerProgressBar layer={row.original} />,
    header: ({ column }) => renderHeader("Progress", column),
  },
  {
    id: "timeout",
    accessorFn: (row) => secondsToHHHMM(row.timeout),
    header: ({ column }) => renderHeader("Timeout", column),
  },
  {
    id: "timeoutLlu",
    accessorFn: (row) => secondsToHHHMM(row.timeoutLlu),
    header: ({ column }) => renderHeader("Timeout LLU", column),
  },
  {
    id: "eligible",
    accessorFn: (row) => (row.eligibleTime ? convertUnixToHumanReadableDate(row.eligibleTime) : ""),
    header: ({ column }) => renderHeader("Eligible", column),
  },
  {
    // The time before which no frame of this layer may start. Set by an
    // operator (Set Start After...) or written automatically by Cuebot's
    // exit-status backoff, e.g. a license shortage. The accessor keeps the
    // raw epoch so sorting stays numeric; the cell formats it and carries
    // the reason as its tooltip.
    id: "startAfter",
    accessorFn: (row) => layerStartAfterSeconds(row),
    sortingFn: (rowA, rowB, columnId) =>
      (rowA.getValue(columnId) as number) - (rowB.getValue(columnId) as number),
    cell: ({ row }) => {
      const startAfter = layerStartAfterSeconds(row.original);
      if (!startAfter) return null;
      const reason = row.original.startAfterReason ?? "";
      return (
        // `title` renders the reason as plain text, so a username embedded in
        // it can never be interpreted as markup.
        <span title={reason || undefined}>{convertUnixToHumanReadableDate(startAfter)}</span>
      );
    },
    header: ({ column }) => renderHeader("Start After", column),
  },
];
