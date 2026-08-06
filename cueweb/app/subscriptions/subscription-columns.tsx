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
import { Subscription } from "@/app/utils/get_utils";

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

// size/burst/reservedCores arrive as centcores (cores * 100); divide by 100 for
// display, matching CueGUI's SubscriptionsWidget. Whole numbers render without
// a decimal; fractional values keep two places.
const toCores = (centcores: number | undefined) => (centcores ?? 0) / 100;
const formatCores = (centcores: number | undefined) => {
  const cores = toCores(centcores);
  return Number.isInteger(cores) ? String(cores) : cores.toFixed(2);
};

// Columns mirror CueGUI's SubscriptionsWidget: Alloc, Usage, Size, Burst, Used.
// Numeric columns sort by their underlying value.
export const subscriptionColumns: ColumnDef<Subscription>[] = [
  {
    accessorKey: "allocationName",
    header: sortableHeader("Alloc"),
    cell: ({ row }) => <span>{row.original.allocationName}</span>,
  },
  {
    id: "usage",
    header: sortableHeader("Usage"),
    // reserved_cores / size (proportion); CueGUI shows it as a percentage.
    accessorFn: (s) => (s.size ? s.reservedCores / s.size : 0),
    cell: ({ row }) => {
      const s = row.original;
      const pct = s.size ? (s.reservedCores / s.size) * 100 : 0;
      return <span>{pct.toFixed(2)}%</span>;
    },
  },
  {
    id: "size",
    header: sortableHeader("Size"),
    accessorFn: (s) => toCores(s.size),
    cell: ({ row }) => <span>{formatCores(row.original.size)}</span>,
  },
  {
    id: "burst",
    header: sortableHeader("Burst"),
    accessorFn: (s) => toCores(s.burst),
    cell: ({ row }) => <span>{formatCores(row.original.burst)}</span>,
  },
  {
    id: "used",
    header: sortableHeader("Used"),
    accessorFn: (s) => toCores(s.reservedCores),
    cell: ({ row }) => <span>{toCores(row.original.reservedCores).toFixed(2)}</span>,
  },
];
