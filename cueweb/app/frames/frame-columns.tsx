"use client";

import { ColumnDef } from "@tanstack/react-table";
import { Button } from "@/components/ui/button";
import { ArrowUpDown } from "lucide-react";
import { convertUnixToHumanReadableDate, convertMemoryToString, secondsToHHMMSS } from "@/app/utils/layers_frames_utils";

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
    accessorKey: "usedMemory",
    header: ({ column }) => <SortingButton column={column} label="Memory" />,
    cell: ({ row }) => getFrameMemory(row.original),
  },
  {
    accessorKey: "usedGpuMemory",
    header: ({ column }) => <SortingButton column={column} label="GPU Memory" />,
    cell: ({ row }) => getFrameGpuMemory(row.original),
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
];
