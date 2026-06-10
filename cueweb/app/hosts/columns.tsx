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
import { Status } from "@/components/ui/status";
import { Host } from "@/app/utils/get_utils";
import { idleRatio, kbStringToHuman, kbStringToNumber } from "@/app/hosts/host_format_utils";

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

export const hostColumns: ColumnDef<Host>[] = [
  {
    accessorKey: "name",
    header: sortableHeader("Name"),
    // Link into the host detail page (procs / comments / tags). stopPropagation
    // so the click doesn't also trigger any row-level handler.
    cell: ({ row }) => (
      <Link
        href={`/hosts/${encodeURIComponent(row.original.name)}`}
        className="text-primary underline-offset-2 hover:underline"
        onClick={(e) => e.stopPropagation()}
      >
        {row.original.name}
      </Link>
    ),
  },
  {
    accessorKey: "state",
    header: sortableHeader("State"),
    cell: ({ row }) => <Status status={row.original.state} />,
  },
  {
    accessorKey: "lockState",
    id: "locked",
    header: sortableHeader("Locked"),
    cell: ({ row }) => <Status status={row.original.lockState} />,
  },
  {
    accessorKey: "nimbyEnabled",
    id: "nimby",
    header: sortableHeader("NIMBY"),
    cell: ({ row }) => <span>{row.original.nimbyEnabled ? "Yes" : "No"}</span>,
  },
  {
    id: "cores",
    header: sortableHeader("Cores (Idle/Total)"),
    // Sort by idle ratio so "most free" sorts together regardless of host size.
    accessorFn: (h) => idleRatio(h.idleCores, h.cores),
    cell: ({ row }) => (
      <span>
        {row.original.idleCores.toFixed(2)} / {row.original.cores.toFixed(2)}
      </span>
    ),
  },
  {
    id: "memory",
    header: sortableHeader("Memory (Idle/Total)"),
    // Sort by idle ratio (matching Cores), not the formatted string.
    accessorFn: (h) => idleRatio(kbStringToNumber(h.idleMemory), kbStringToNumber(h.totalMemory)),
    cell: ({ row }) => (
      <span>
        {kbStringToHuman(row.original.idleMemory)} / {kbStringToHuman(row.original.totalMemory)}
      </span>
    ),
  },
  {
    id: "freeMcp",
    header: sortableHeader("Free /mcp"),
    accessorFn: (h) => kbStringToNumber(h.freeMcp),
    cell: ({ row }) => <span>{kbStringToHuman(row.original.freeMcp)}</span>,
  },
];
