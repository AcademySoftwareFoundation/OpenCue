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
import { Limit } from "@/app/utils/get_utils";

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

// Columns mirror CueGUI's Limits window: Limit Name, Max Value, Current
// Running. Numeric columns sort by their underlying value.
export const limitColumns: ColumnDef<Limit>[] = [
  {
    accessorKey: "name",
    header: sortableHeader("Limit Name"),
    cell: ({ row }) => <span className="break-all">{row.original.name}</span>,
  },
  {
    accessorKey: "maxValue",
    header: sortableHeader("Max Value"),
    cell: ({ row }) => <span>{row.original.maxValue}</span>,
  },
  {
    accessorKey: "currentRunning",
    header: sortableHeader("Current Running"),
    cell: ({ row }) => <span>{row.original.currentRunning}</span>,
  },
];
