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
import { ArrowUpDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Proc } from "@/app/utils/get_utils";
import { kbStringToHuman, kbStringToNumber } from "@/app/hosts/host_format_utils";
import { secondsToHumanAge } from "@/app/utils/layers_frames_utils";

function sortableHeader(label: string) {
  // eslint-disable-next-line react/display-name
  return ({ column }: { column: any }) => (
    <Button
      variant="ghost"
      size="sm"
      className="-mx-2 h-7 px-1.5 text-xs font-medium"
      onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
    >
      {label}
      <ArrowUpDown className="ml-1 h-3 w-3 opacity-60" />
    </Button>
  );
}

// Runtime (how long this proc has been on its current frame) derived from
// the dispatch timestamp. Computed at render time; the host detail page
// re-renders every 15s so the value stays roughly live.
function procRuntimeSeconds(dispatchTime: number): number {
  if (!dispatchTime) return 0;
  return Math.max(0, Math.floor(Date.now() / 1000) - dispatchTime);
}

export const procColumns: ColumnDef<Proc>[] = [
  {
    accessorKey: "jobName",
    header: sortableHeader("Job"),
    cell: ({ row }) => <span className="break-all">{row.original.jobName}</span>,
  },
  {
    accessorKey: "frameName",
    header: sortableHeader("Frame"),
    cell: ({ row }) => <span className="break-all">{row.original.frameName}</span>,
  },
  {
    accessorKey: "reservedCores",
    id: "cores",
    header: sortableHeader("Cores"),
    cell: ({ row }) => <span>{row.original.reservedCores.toFixed(2)}</span>,
  },
  {
    id: "reservedMemory",
    header: sortableHeader("Reserved Mem"),
    accessorFn: (p) => kbStringToNumber(p.reservedMemory),
    cell: ({ row }) => <span>{kbStringToHuman(row.original.reservedMemory)}</span>,
  },
  {
    id: "usedMemory",
    header: sortableHeader("Used Mem"),
    accessorFn: (p) => kbStringToNumber(p.usedMemory),
    cell: ({ row }) => <span>{kbStringToHuman(row.original.usedMemory)}</span>,
  },
  {
    id: "services",
    header: sortableHeader("Services"),
    accessorFn: (p) => (p.services ?? []).join(", "),
    cell: ({ row }) => <span>{(row.original.services ?? []).join(", ") || "-"}</span>,
  },
  {
    id: "runtime",
    header: sortableHeader("Runtime"),
    // Sort by elapsed runtime: a smaller dispatchTime means a longer
    // runtime, so negate to keep "longest running" sorting together.
    accessorFn: (p) => -procRuntimeSeconds(p.dispatchTime),
    cell: ({ row }) => <span>{secondsToHumanAge(procRuntimeSeconds(row.original.dispatchTime))}</span>,
  },
];
