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
import { AllocationRow } from "@/app/allocations/allocation-utils";

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

// Cores are floats in the proto but CueGUI shows them as integers.
const asInt = (n: number | undefined) => Math.round(n ?? 0);

// Columns mirror CueGUI's Allocations window. Header labels repeat; the column ids are unique.
export const allocationColumns: ColumnDef<AllocationRow>[] = [
  {
    accessorKey: "name",
    header: sortableHeader("Name"),
    // Click-through to the hosts page filtered to this allocation (the hosts
    // filter itself is a separate task; the param is forward-compatible).
    cell: ({ row }) => (
      <Link
        href={`/hosts?allocation=${encodeURIComponent(row.original.name)}`}
        className="text-primary underline-offset-2 hover:underline"
      >
        {row.original.name}
      </Link>
    ),
  },
  {
    accessorKey: "tag",
    header: sortableHeader("Tag"),
    cell: ({ row }) => <span>{row.original.tag}</span>,
  },
  {
    id: "cores",
    header: sortableHeader("Cores"),
    accessorFn: (a) => a.stats?.cores ?? 0,
    cell: ({ row }) => <span>{asInt(row.original.stats?.cores)}</span>,
  },
  {
    id: "idle",
    header: sortableHeader("Idle"),
    accessorFn: (a) => a.stats?.availableCores ?? 0,
    cell: ({ row }) => <span>{asInt(row.original.stats?.availableCores)}</span>,
  },
  {
    id: "lockedCores",
    header: sortableHeader("Locked"),
    accessorFn: (a) => a.stats?.lockedCores ?? 0,
    cell: ({ row }) => <span>{asInt(row.original.stats?.lockedCores)}</span>,
  },
  {
    id: "downCores",
    header: sortableHeader("Down"),
    accessorFn: (a) => a.downCores,
    cell: ({ row }) => <span>{asInt(row.original.downCores)}</span>,
  },
  {
    id: "repairCores",
    header: sortableHeader("Repair"),
    accessorFn: (a) => a.repairCores,
    cell: ({ row }) => <span>{asInt(row.original.repairCores)}</span>,
  },
  {
    id: "hosts",
    header: sortableHeader("Hosts"),
    accessorFn: (a) => a.stats?.hosts ?? 0,
    cell: ({ row }) => <span>{row.original.stats?.hosts ?? 0}</span>,
  },
  {
    id: "lockedHosts",
    header: sortableHeader("Locked"),
    accessorFn: (a) => a.stats?.lockedHosts ?? 0,
    cell: ({ row }) => <span>{row.original.stats?.lockedHosts ?? 0}</span>,
  },
  {
    id: "downHosts",
    header: sortableHeader("Down"),
    accessorFn: (a) => a.stats?.downHosts ?? 0,
    cell: ({ row }) => <span>{row.original.stats?.downHosts ?? 0}</span>,
  },
  {
    id: "repairHosts",
    header: sortableHeader("Repair"),
    accessorFn: (a) => a.repairHosts,
    cell: ({ row }) => <span>{row.original.repairHosts}</span>,
  },
];
