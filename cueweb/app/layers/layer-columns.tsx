"use client";

import { ColumnDef } from "@tanstack/react-table";
import { Button } from "@/components/ui/button";
import { ArrowUpDown } from "lucide-react";
import { convertMemoryToString, secondsToHHMMSS, secondsToHHHMM } from "@/app/utils/layers_frames_utils";

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
  if (layer.layerStats.totalFrames === 0) return "0%";
  const completed = (layer.layerStats.succeededFrames / layer.layerStats.totalFrames) * 100.0;
  return `${completed.toFixed(2)}%`;
};

const renderHeader = (title: string, column: any) => (
  <Button variant="ghost" className="px-1 py-1 mx-0" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
    {title}
    <ArrowUpDown className="ml-1 h-4 w-3" />
  </Button>
);

export const layerColumns: ColumnDef<Layer>[] = [
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
    accessorFn: (row) => getPercentCompleted(row),
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
];
