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

import * as React from "react";

import type { Subscription } from "@/app/utils/get_utils";
import { Skeleton } from "@/components/ui/skeleton";

/**
 * Subscription Graphs (CueGUI SubscriptionGraphWidget / SubBookingBarDelegate
 * parity). Each subscription is one horizontal bar scaled to the *allocation's*
 * total core count (not the subscription's own size), mirroring CueGUI:
 *   - a sky-blue track spans the allocation's core capacity,
 *   - a yellow-green fill from the left shows the cores currently reserved
 *     (in use) by the subscription,
 *   - a blue vertical marker sits at the subscription size,
 *   - a red vertical marker sits at the subscription burst.
 * Hovering shows the exact in-use / size / burst / allocation values.
 */

// CueGUI RGB_FRAME_STATE + DarkPalette colors.
const ALLOC_TRACK = "#87cfeb"; // WAITING sky-blue (135,207,235): allocation capacity
const RUNNING_FILL = "#c8c837"; // RUNNING yellow-green (200,200,55): reserved/in-use cores
const SIZE_MARKER = "#58a3d1"; // PAUSE_ICON blue (88,163,209): subscription size
const BURST_MARKER = "#e03434"; // KILL_ICON red (224,52,52): subscription burst

// size/burst/reservedCores arrive as centcores (cores * 100); divide by 100 for
// display. Allocation stats.cores is already in whole cores. Whole numbers
// render without a decimal, fractions keep two places.
const toCores = (centcores: number | undefined) => (centcores ?? 0) / 100;
const fmt = (cores: number) => (Number.isInteger(cores) ? String(cores) : cores.toFixed(2));

// A single subscription's horizontal bar plus its allocation-name label. The
// whole row forwards right-clicks so the page can raise the context menu.
function SubscriptionBar({
  sub,
  allocCores,
  onContextMenu,
}: {
  sub: Subscription;
  allocCores: Record<string, number>;
  onContextMenu?: (e: React.MouseEvent, sub: Subscription) => void;
}) {
  const inUse = toCores(sub.reservedCores);
  const size = toCores(sub.size);
  const burst = toCores(sub.burst);
  const alloc = allocCores[sub.allocationName] ?? 0;

  // CueGUI scales the bar to the allocation's total core count. When that is
  // unknown (allocations not loaded yet), fall back to the largest sub value so
  // the markers still render. Burst can exceed the allocation, so include it in
  // the domain to keep the red marker on-screen.
  const domainMax = Math.max(alloc, size, burst, inUse, 1);
  const pct = (v: number) => Math.max(0, Math.min(100, (v / domainMax) * 100));

  const [tipX, setTipX] = React.useState<number | null>(null);
  const usageText = size > 0 ? `${((inUse / size) * 100).toFixed(2)}%` : inUse > 0 ? "∞" : "—";

  return (
    <div
      className="flex items-center gap-3 rounded px-1 py-0.5 hover:bg-muted/40"
      onContextMenu={onContextMenu ? (e) => onContextMenu(e, sub) : undefined}
    >
      <span className="w-40 shrink-0 truncate text-sm" title={sub.allocationName}>
        {sub.allocationName}
      </span>
      <div
        className="relative h-[18px] min-w-0 flex-1 rounded bg-muted/40"
        onMouseEnter={(e) => setTipX(e.nativeEvent.offsetX)}
        onMouseMove={(e) => setTipX(e.nativeEvent.offsetX)}
        onMouseLeave={() => setTipX(null)}
      >
        {/* Allocation capacity (sky-blue). */}
        <div
          className="absolute inset-y-0 left-0 rounded-l"
          style={{ width: `${pct(alloc)}%`, backgroundColor: ALLOC_TRACK }}
        />
        {/* Reserved / in-use cores (yellow-green), drawn over the capacity. */}
        <div
          className="absolute inset-y-0 left-0 rounded-l"
          style={{ width: `${pct(inUse)}%`, backgroundColor: RUNNING_FILL }}
        />
        {/* Blue size marker, red burst marker (CueGUI parity). */}
        <div
          className="absolute inset-y-0 w-[3px] -translate-x-1/2"
          style={{ left: `${pct(size)}%`, backgroundColor: SIZE_MARKER }}
        />
        <div
          className="absolute inset-y-0 w-[3px] -translate-x-1/2"
          style={{ left: `${pct(burst)}%`, backgroundColor: BURST_MARKER }}
        />

        {tipX !== null ? (
          <div
            className="pointer-events-none absolute bottom-full z-10 mb-1 -translate-x-1/2 whitespace-nowrap rounded-md border bg-popover px-3 py-2 text-xs text-popover-foreground shadow-md"
            style={{ left: tipX }}
          >
            <div className="mb-1 font-medium">{sub.allocationName}</div>
            <div className="grid grid-cols-[auto_auto] gap-x-3 gap-y-0.5">
              <span className="text-muted-foreground">In use</span>
              <span className="text-right tabular-nums">{fmt(inUse)}</span>
              <span className="text-muted-foreground">Size</span>
              <span className="text-right tabular-nums">{fmt(size)}</span>
              <span className="text-muted-foreground">Burst</span>
              <span className="text-right tabular-nums">{fmt(burst)}</span>
              <span className="text-muted-foreground">Allocation</span>
              <span className="text-right tabular-nums">{alloc > 0 ? fmt(alloc) : "—"}</span>
              <span className="text-muted-foreground">Usage</span>
              <span className="text-right tabular-nums">{usageText}</span>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}

// One show's section: a show-name label followed by one bar per subscription.
export function ShowSubscriptionGraph({
  showName,
  subscriptions,
  allocCores,
  onSubContextMenu,
  onShowContextMenu,
}: {
  showName: string;
  subscriptions: Subscription[] | null;
  allocCores: Record<string, number>;
  onSubContextMenu?: (e: React.MouseEvent, sub: Subscription) => void;
  onShowContextMenu?: (e: React.MouseEvent, showName: string) => void;
}) {
  const sorted = React.useMemo(
    () =>
      subscriptions
        ? [...subscriptions].sort((a, b) => a.allocationName.localeCompare(b.allocationName))
        : null,
    [subscriptions],
  );

  return (
    // The whole section forwards right-clicks so an empty show can still raise
    // the "Add new subscription" menu (CueGUI parity). Subscription bars stop
    // propagation so they keep their own (sub-specific) menu.
    <section
      className="mb-6"
      onContextMenu={onShowContextMenu ? (e) => onShowContextMenu(e, showName) : undefined}
    >
      <h2 className="mb-2 text-sm font-medium">{showName}</h2>
      {sorted === null ? (
        <div className="space-y-2">
          <Skeleton className="h-7 w-full" />
          <Skeleton className="h-7 w-full" />
        </div>
      ) : sorted.length === 0 ? (
        <p className="px-1 text-sm text-muted-foreground">
          This show has no subscriptions. Right-click to add one.
        </p>
      ) : (
        <div className="space-y-0.5">
          {sorted.map((sub) => (
            <SubscriptionBar
              key={sub.id || sub.name}
              sub={sub}
              allocCores={allocCores}
              onContextMenu={onSubContextMenu}
            />
          ))}
        </div>
      )}
    </section>
  );
}
