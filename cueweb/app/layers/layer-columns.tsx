"use client";

import { ColumnDef } from "@tanstack/react-table";
import { Button } from "@/components/ui/button";
import { ArrowUpDown, MoreHorizontal } from "lucide-react";
import { convertMemoryToString, secondsToHHMMSS, secondsToHHHMM } from "@/app/utils/utils";

// This type is used to define the shape of our data.
// You can use a Zod schema here if you want.
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
};

const getPercentCompleted = (layer: Layer) => {
  const completed = (layer.layerStats.succeededFrames / layer.layerStats.totalFrames) * 100.0;
  return `${completed}%`;
};

export const layerColumns: ColumnDef<Layer>[] = [
  // accessorKey is the unique id for each column, header is the string that shows as the header in the row
  {
    accessorKey: "dispatchOrder",
    header: ({ column }) => {
      return (
        <Button variant="ghost" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
          Dispatch Order
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      );
    },
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
  },
  {
    accessorKey: "services",
    header: ({ column }) => {
      return (
        <Button variant="ghost" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
          Services
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      );
    },
  },
  {
    accessorKey: "limits",
    header: ({ column }) => {
      return (
        <Button variant="ghost" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
          Limits
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      );
    },
  },
  {
    accessorKey: "range",
    header: ({ column }) => {
      return (
        <Button variant="ghost" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
          Range
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      );
    },
  },
  {
    accessorKey: "minCores",
    header: ({ column }) => {
      return (
        <Button variant="ghost" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
          Cores
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      );
    },
  },
  {
    id: "minMemory",
    accessorFn: (row) => convertMemoryToString(Number.parseInt(row.minMemory), JSON.stringify(row)),
    header: ({ column }) => {
      return (
        <Button variant="ghost" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
          Memory
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      );
    },
  },
  {
    accessorKey: "minGpus",
    header: ({ column }) => {
      return (
        <Button variant="ghost" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
          Gpus
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      );
    },
  },
  {
    id: "minGpuMemory",
    accessorFn: (row) => convertMemoryToString(Number.parseInt(row.minGpuMemory), JSON.stringify(row)),
    header: ({ column }) => {
      return (
        <Button variant="ghost" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
          Gpu Memory
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      );
    },
  },
  {
    id: "maxRss",
    accessorFn: (row) => convertMemoryToString(Number.parseInt(row.layerStats.maxRss), JSON.stringify(row)),
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
    id: "totalFrames",
    accessorFn: (row) => row.layerStats.totalFrames,
    header: ({ column }) => {
      return (
        <Button variant="ghost" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
          Total
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      );
    },
  },
  {
    id: "succeededFrames",
    accessorFn: (row) => row.layerStats.succeededFrames,
    header: ({ column }) => {
      return (
        <Button variant="ghost" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
          Done
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      );
    },
  },
  {
    id: "runningFrames",
    accessorFn: (row) => row.layerStats.runningFrames,
    header: ({ column }) => {
      return (
        <Button variant="ghost" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
          Run
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      );
    },
  },
  {
    id: "dependFrames",
    accessorFn: (row) => row.layerStats.dependFrames,
    header: ({ column }) => {
      return (
        <Button variant="ghost" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
          Depend
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      );
    },
  },
  {
    id: "waitingFrames",
    accessorFn: (row) => row.layerStats.waitingFrames,
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
    id: "eatenFrames",
    accessorFn: (row) => row.layerStats.eatenFrames,
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
    id: "deadFrames",
    accessorFn: (row) => row.layerStats.deadFrames,
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
    id: "avgFrameSec",
    accessorFn: (row) => secondsToHHMMSS(row.layerStats.avgFrameSec),
    header: ({ column }) => {
      return (
        <Button variant="ghost" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
          Avg
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      );
    },
  },
  {
    accessorKey: "tags",
    header: ({ column }) => {
      return (
        <Button variant="ghost" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
          Tags
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      );
    },
  },
  {
    id: "progress",
    accessorFn: (row) => getPercentCompleted(row),
    header: ({ column }) => {
      return (
        <Button variant="ghost" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
          Progress
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      );
    },
  },
  {
    id: "timeout",
    accessorFn: (row) => secondsToHHHMM(row.timeout),
    header: ({ column }) => {
      return (
        <Button variant="ghost" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
          Timeout
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      );
    },
  },
  {
    id: "timeoutLlu",
    accessorFn: (row) => secondsToHHHMM(row.timeoutLlu),
    header: ({ column }) => {
      return (
        <Button variant="ghost" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
          Timeout LLU
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      );
    },
  },
];
