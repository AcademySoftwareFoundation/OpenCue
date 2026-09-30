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
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Show } from "@/app/utils/get_utils";

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

// Columns mirror CueGUI's ShowsWidget: Show Name, Cores Run (reserved_cores),
// Frames Run (running_frames), Frames Pending (pending_frames), Jobs
// (pending_jobs). Numeric columns sort by their underlying value.
export const showColumns: ColumnDef<Show>[] = [
  {
    accessorKey: "name",
    header: sortableHeader("Show Name"),
    cell: ({ row }) => (
      <Link
        href={`/shows/${encodeURIComponent(row.original.name)}`}
        className="text-primary underline-offset-2 hover:underline"
        onClick={(e) => e.stopPropagation()}
      >
        {row.original.name}
      </Link>
    ),
  },
  {
    id: "coresRun",
    header: sortableHeader("Cores Run"),
    accessorFn: (s) => s.showStats?.reservedCores ?? 0,
    cell: ({ row }) => <span>{(row.original.showStats?.reservedCores ?? 0).toFixed(2)}</span>,
  },
  {
    id: "framesRun",
    header: sortableHeader("Frames Run"),
    accessorFn: (s) => s.showStats?.runningFrames ?? 0,
    cell: ({ row }) => <span>{row.original.showStats?.runningFrames ?? 0}</span>,
  },
  {
    id: "framesPending",
    header: sortableHeader("Frames Pending"),
    accessorFn: (s) => s.showStats?.pendingFrames ?? 0,
    cell: ({ row }) => <span>{row.original.showStats?.pendingFrames ?? 0}</span>,
  },
  {
    id: "jobs",
    header: sortableHeader("Jobs"),
    accessorFn: (s) => s.showStats?.pendingJobs ?? 0,
    cell: ({ row }) => <span>{row.original.showStats?.pendingJobs ?? 0}</span>,
  },
];
