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
import { ArrowUpDown, MessageSquare } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Host } from "@/app/utils/get_utils";
import { kbStringToHuman, kbStringToNumber } from "@/app/hosts/host_format_utils";
import { OPEN_HOST_COMMENTS_EVENT } from "@/components/ui/host-action-events";

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

// Red (used) + green (free) horizontal bar, mirroring CueGUI's Host*BarDelegate.
function MemBar({ usedKb, totalKb }: { usedKb: number; totalKb: number }) {
  const pct = totalKb > 0 ? Math.min(100, Math.max(0, (usedKb / totalKb) * 100)) : 0;
  return (
    <div className="flex h-3.5 w-16 overflow-hidden rounded-sm border border-border/50" title={`${pct.toFixed(0)}% used`}>
      <div className="bg-red-500" style={{ width: `${pct}%` }} />
      <div className="bg-green-600" style={{ width: `${100 - pct}%` }} />
    </div>
  );
}

const kb = (v?: string) => kbStringToNumber(v ?? "");

function formatBootTime(epoch: number): string {
  if (!epoch) return "";
  const d = new Date(epoch * 1000);
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  const hh = String(d.getHours()).padStart(2, "0");
  const mi = String(d.getMinutes()).padStart(2, "0");
  return `${mm}/${dd} ${hh}:${mi}`;
}

function openComments(host: Host) {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new CustomEvent(OPEN_HOST_COMMENTS_EVENT, { detail: { hosts: [host] } }));
}

// Full CueGUI Monitor Hosts column set. Header labels mirror CueGUI; numeric /
// memory columns sort by their underlying value, the bar columns by free space.
export const hostColumns: ColumnDef<Host>[] = [
  {
    accessorKey: "name",
    header: sortableHeader("Name"),
    cell: ({ row }) => (
      <div className="flex items-center gap-1">
        <Link
          href={`/hosts/${encodeURIComponent(row.original.name)}`}
          className="text-primary underline-offset-2 hover:underline"
          onClick={(e) => e.stopPropagation()}
        >
          {row.original.name}
        </Link>
        {row.original.hasComment ? (
          <button
            title="View comments"
            onClick={(e) => {
              e.stopPropagation();
              openComments(row.original);
            }}
          >
            <MessageSquare className="h-3.5 w-3.5 text-amber-500" />
          </button>
        ) : null}
      </div>
    ),
  },
  {
    id: "load",
    header: sortableHeader("Load %"),
    accessorFn: (h) => (h.cores ? (h.load ?? 0) / h.cores : 0),
    cell: ({ row }) => {
      const h = row.original;
      const pct = h.cores ? (h.load ?? 0) / h.cores : 0;
      return <span className="tabular-nums">{Math.round(pct)}%</span>;
    },
  },
  {
    id: "swap",
    header: sortableHeader("Swap"),
    accessorFn: (h) => kb(h.freeSwap),
    cell: ({ row }) => <MemBar usedKb={kb(row.original.totalSwap) - kb(row.original.freeSwap)} totalKb={kb(row.original.totalSwap)} />,
  },
  {
    id: "physical",
    header: sortableHeader("Physical"),
    accessorFn: (h) => kb(h.freeMemory),
    cell: ({ row }) => <MemBar usedKb={kb(row.original.totalMemory) - kb(row.original.freeMemory)} totalKb={kb(row.original.totalMemory)} />,
  },
  {
    id: "gpuMemoryBar",
    header: sortableHeader("GPU Memory"),
    accessorFn: (h) => kb(h.freeGpuMemory),
    cell: ({ row }) => <MemBar usedKb={kb(row.original.totalGpuMemory) - kb(row.original.freeGpuMemory)} totalKb={kb(row.original.totalGpuMemory)} />,
  },
  {
    id: "totalMemory",
    header: sortableHeader("Total Memory"),
    accessorFn: (h) => kb(h.memory),
    cell: ({ row }) => <span>{kbStringToHuman(row.original.memory)}</span>,
  },
  {
    id: "idleMemory",
    header: sortableHeader("Idle Memory"),
    accessorFn: (h) => kb(h.idleMemory),
    cell: ({ row }) => <span>{kbStringToHuman(row.original.idleMemory)}</span>,
  },
  {
    id: "temp",
    header: sortableHeader("Temp"),
    accessorFn: (h) => kb(h.freeMcp),
    cell: ({ row }) => <MemBar usedKb={kb(row.original.totalMcp) - kb(row.original.freeMcp)} totalKb={kb(row.original.totalMcp)} />,
  },
  {
    id: "tempFree",
    header: sortableHeader("Temp Free"),
    accessorFn: (h) => kb(h.freeMcp),
    cell: ({ row }) => <span>{kbStringToHuman(row.original.freeMcp)}</span>,
  },
  {
    id: "tempFreePct",
    header: sortableHeader("Temp Free %"),
    accessorFn: (h) => (kb(h.totalMcp) ? kb(h.freeMcp) / kb(h.totalMcp) : 0),
    cell: ({ row }) => {
      const total = kb(row.original.totalMcp);
      if (!total) return <span />;
      return <span className="tabular-nums">{Math.round((100 * kb(row.original.freeMcp)) / total)}%</span>;
    },
  },
  {
    id: "cores",
    header: sortableHeader("Cores"),
    accessorFn: (h) => h.cores,
    cell: ({ row }) => <span className="tabular-nums">{row.original.cores.toFixed(2)}</span>,
  },
  {
    id: "idleCores",
    header: sortableHeader("Idle Cores"),
    accessorFn: (h) => h.idleCores,
    cell: ({ row }) => <span className="tabular-nums">{row.original.idleCores.toFixed(2)}</span>,
  },
  {
    id: "gpus",
    header: sortableHeader("GPUs"),
    accessorFn: (h) => h.gpus ?? 0,
    cell: ({ row }) => <span className="tabular-nums">{row.original.gpus ?? 0}</span>,
  },
  {
    id: "idleGpus",
    header: sortableHeader("Idle GPUs"),
    accessorFn: (h) => h.idleGpus ?? 0,
    cell: ({ row }) => <span className="tabular-nums">{row.original.idleGpus ?? 0}</span>,
  },
  {
    id: "gpuMem",
    header: sortableHeader("GPU Mem"),
    accessorFn: (h) => kb(h.gpuMemory),
    cell: ({ row }) => <span>{kbStringToHuman(row.original.gpuMemory ?? "")}</span>,
  },
  {
    id: "gpuMemIdle",
    header: sortableHeader("GPU Mem Idle"),
    accessorFn: (h) => kb(h.idleGpuMemory),
    cell: ({ row }) => <span>{kbStringToHuman(row.original.idleGpuMemory ?? "")}</span>,
  },
  {
    id: "ping",
    header: sortableHeader("Ping"),
    accessorFn: (h) => h.pingTime ?? 0,
    cell: ({ row }) => {
      const ping = row.original.pingTime ? Math.max(0, Math.round(Date.now() / 1000 - row.original.pingTime)) : 0;
      return <span className="tabular-nums">{ping}</span>;
    },
  },
  {
    id: "bootTime",
    header: sortableHeader("Boot Time"),
    accessorFn: (h) => h.bootTime ?? 0,
    cell: ({ row }) => <span className="tabular-nums">{formatBootTime(row.original.bootTime)}</span>,
  },
  {
    accessorKey: "state",
    id: "hardware",
    header: sortableHeader("Hardware"),
    cell: ({ row }) => <span>{row.original.state}</span>,
  },
  {
    accessorKey: "lockState",
    id: "locked",
    header: sortableHeader("Locked"),
    cell: ({ row }) => <span>{row.original.lockState}</span>,
  },
  {
    id: "threadMode",
    header: sortableHeader("ThreadMode"),
    accessorFn: (h) => h.threadMode ?? "",
    cell: ({ row }) => <span>{row.original.threadMode ?? ""}</span>,
  },
  {
    id: "os",
    header: sortableHeader("OS"),
    accessorFn: (h) => h.os ?? "",
    cell: ({ row }) => <span>{row.original.os ?? ""}</span>,
  },
  {
    id: "tags",
    header: sortableHeader("Tags"),
    accessorFn: (h) => (h.tags ?? []).join(","),
    cell: ({ row }) => <span className="truncate" title={(row.original.tags ?? []).join(", ")}>{(row.original.tags ?? []).join(", ")}</span>,
  },
];

// Row tint by state/lock (CueGUI HostWidgetItem BackgroundRole). Returns a
// Tailwind class for SimpleDataTable's getRowClassName hook.
export function hostRowClassName(host: Host): string | undefined {
  if (host.state === "REBOOT_WHEN_IDLE") return "bg-amber-950/40";
  if (host.state !== "UP") return "bg-red-950/40";
  if (host.lockState === "LOCKED") return "bg-yellow-950/40";
  return undefined;
}
