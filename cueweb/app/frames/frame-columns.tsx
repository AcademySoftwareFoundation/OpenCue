"use client";

import { ColumnDef } from "@tanstack/react-table";
import { Button } from "@/components/ui/button";
import { ArrowUpDown } from "lucide-react";
import { convertUnixToHumanReadableDate, convertMemoryToString, secondsToHHMMSS } from "../utils/utils";

// This type is used to define the shape of our data.
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
  frameStateDisplayOverride: string; //??
};

// cuegui.cuegui.FrameMonitorTree.getCores() contains logic for getting cores a frame is using
const getFrameCores = (frame: Frame) => {
  const cores = frame.lastResource.split("/")[1];
  return cores;
};

// cuegui.cuegui.FrameMonitorTree.getGpus() contains logic for getting gpus a frame is using
// the gpus are the last digit in the host (lastResource) name
const getFrameGpus = (frame: Frame) => {
  const gpus = frame.lastResource.split("/")[2];
  return gpus;
};

const getFrameMemory = (frame: Frame) => {
  if (frame.state == "RUNNING") {
    return convertMemoryToString(parseInt(frame.usedMemory), JSON.stringify(frame));
  }
  return convertMemoryToString(parseInt(frame.maxRss), JSON.stringify(frame));
};

const getFrameGpuMemory = (frame: Frame) => {
  if (frame.state == "RUNNING") {
    return convertMemoryToString(parseInt(frame.usedGpuMemory), JSON.stringify(frame));
  }
  return convertMemoryToString(parseInt(frame.maxGpuMemory), JSON.stringify(frame));
};

const getFrameRuntime = (frame: Frame) => {
  if (frame.stopTime != 0) {
    return secondsToHHMMSS(frame.stopTime - frame.startTime);
  }
  if (frame.startTime != 0) {
    const currentDate = new Date();
    const timestampInSeconds = currentDate.getTime() / 1000;
    return secondsToHHMMSS(timestampInSeconds - frame.startTime);
  }
  return "00:00:00";
};

export const frameColumns: ColumnDef<Frame>[] = [
  // accessorKey is the unique id for each column, header is the string that shows as the header in the row
  {
    accessorKey: "dispatchOrder",
    header: ({ column }) => {
      return (
        <Button variant="ghost" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
          Order
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      );
    },
  },
  {
    accessorKey: "number",
    header: ({ column }) => {
      return (
        <Button variant="ghost" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
          Frame
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      );
    },
  },
  {
    accessorKey: "layerName",
    header: ({ column }) => {
      return (
        <Button variant="ghost" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
          Layer
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      );
    },
  },
  {
    accessorKey: "state",
    header: ({ column }) => {
      return (
        <Button variant="ghost" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
          Status
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      );
    },
  },
  {
    accessorKey: "cores",
    header: ({ column }) => {
      return (
        <Button variant="ghost" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
          Cores
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      );
    },
    cell: ({ row }) => getFrameCores(row.original),
  },
  {
    accessorKey: "gpus",
    header: ({ column }) => {
      return (
        <Button variant="ghost" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
          GPUs
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      );
    },
    cell: ({ row }) => getFrameGpus(row.original),
  },
  {
    accessorKey: "lastResource",
    header: ({ column }) => {
      return (
        <Button variant="ghost" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
          Host
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      );
    },
  },
  {
    accessorKey: "retryCount",
    header: ({ column }) => {
      return (
        <Button variant="ghost" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
          Retries
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      );
    },
  },
  {
    accessorKey: "checkpointCount",
    header: ({ column }) => {
      return (
        <Button variant="ghost" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
          CheckP
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      );
    },
  },
  {
    id: "runtime",
    accessorFn: (row) => getFrameRuntime(row),
    header: ({ column }) => {
      return (
        <Button variant="ghost" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
          Runtime
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      );
    },
  },
  {
    accessorKey: "llu??",
    header: ({ column }) => {
      return (
        <Button variant="ghost" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
          LLU
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      );
    },
  },
  {
    accessorKey: "usedMemory",
    header: ({ column }) => {
      return (
        <Button variant="ghost" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
          Memory
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      );
    },
    cell: ({ row }) => getFrameMemory(row.original),
  },
  {
    accessorKey: "usedGpuMemory",
    header: ({ column }) => {
      return (
        <Button variant="ghost" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
          GPU Memory
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      );
    },
    cell: ({ row }) => getFrameGpuMemory(row.original),
  },
  {
    accessorKey: "remain??",
    header: ({ column }) => {
      return (
        <Button variant="ghost" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
          Remain
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      );
    },
  },
  {
    accessorKey: "startTime",
    header: ({ column }) => {
      return (
        <Button variant="ghost" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
          Start Time
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      );
    },
    cell: ({ row }) => convertUnixToHumanReadableDate(row.original.startTime),
  },
  {
    accessorKey: "stopTime",
    header: ({ column }) => {
      return (
        <Button variant="ghost" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
          Stop Time
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      );
    },
    cell: ({ row }) => convertUnixToHumanReadableDate(row.original.stopTime),
  },
  {
    accessorKey: "lastLine??",
    header: ({ column }) => {
      return (
        <Button variant="ghost" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
          Last Line
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      );
    },
  },
];
