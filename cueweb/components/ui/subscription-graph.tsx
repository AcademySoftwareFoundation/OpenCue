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
import {
  Bar,
  BarChart,
  Cell,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { Subscription } from "@/app/utils/get_utils";
import { Skeleton } from "@/components/ui/skeleton";

/**
 * Subscription Graphs (CueGUI SubscriptionGraphWidget parity). Each subscription
 * is drawn as a horizontal bar whose length is the in-use (reserved) cores. A
 * blue marker line sits at the subscription size and a red marker line at the
 * burst, mirroring CueGUI's SubBookingBarDelegate. The bar turns red when
 * in-use exceeds the subscribed size (overused). Hovering shows the exact
 * in-use / size / burst values.
 */

// CueGUI colors (Style.ColorTheme): size marker = PAUSE_ICON (88,163,209),
// burst marker = KILL_ICON (224,52,52); the bar uses the light-blue WAITING
// tone (135,207,235), red when overused.
const BAR_NORMAL = "#87cfeb";
const BAR_OVERUSED = "#e03434";
const SIZE_MARKER = "#58a3d1";
const BURST_MARKER = "#e03434";
const TRACK = "rgba(127,127,127,0.18)";

// size/burst/reservedCores are centcores (cores * 100); divide by 100 for
// display. Whole numbers render without a decimal, fractions keep two places.
const toCores = (centcores: number | undefined) => (centcores ?? 0) / 100;
const fmt = (cores: number) => (Number.isInteger(cores) ? String(cores) : cores.toFixed(2));

type BarDatum = {
  name: string;
  inUse: number;
  size: number;
  burst: number;
};

function GraphTooltip({ active, payload }: { active?: boolean; payload?: any[] }) {
  if (!active || !payload || payload.length === 0) return null;
  const d = payload[0]?.payload as BarDatum | undefined;
  if (!d) return null;
  // Surface the zero-size anomaly instead of collapsing it to 0.00%: a
  // subscription with no size but live usage is "∞", and a genuinely empty
  // subscription (no size, no usage) is "—".
  const usageText =
    d.size > 0 ? `${((d.inUse / d.size) * 100).toFixed(2)}%` : d.inUse > 0 ? "∞" : "—";
  return (
    <div className="rounded-md border bg-popover px-3 py-2 text-xs text-popover-foreground shadow-md">
      <div className="mb-1 font-medium">{d.name}</div>
      <div className="grid grid-cols-[auto_auto] gap-x-3 gap-y-0.5">
        <span className="text-muted-foreground">In use</span>
        <span className="text-right tabular-nums">{fmt(d.inUse)}</span>
        <span className="text-muted-foreground">Size</span>
        <span className="text-right tabular-nums">{fmt(d.size)}</span>
        <span className="text-muted-foreground">Burst</span>
        <span className="text-right tabular-nums">{fmt(d.burst)}</span>
        <span className="text-muted-foreground">Usage</span>
        <span className="text-right tabular-nums">{usageText}</span>
      </div>
    </div>
  );
}

// A single subscription's horizontal bar plus its allocation-name label. The
// whole row forwards right-clicks so the page can raise the context menu.
function SubscriptionBar({
  sub,
  onContextMenu,
}: {
  sub: Subscription;
  onContextMenu?: (e: React.MouseEvent, sub: Subscription) => void;
}) {
  const inUse = toCores(sub.reservedCores);
  const size = toCores(sub.size);
  const burst = toCores(sub.burst);
  const overused = inUse > size;

  // Scale to the largest of the three values so the size/burst markers sit near
  // the right edge (with a little headroom) and the in-use fill reads relative
  // to them. Guard against an all-zero subscription.
  const domainMax = Math.max(inUse, size, burst, 1) * 1.05;
  const data: BarDatum[] = [{ name: sub.allocationName, inUse, size, burst }];

  return (
    <div
      className="flex items-center gap-3 rounded px-1 py-0.5 hover:bg-muted/40"
      onContextMenu={onContextMenu ? (e) => onContextMenu(e, sub) : undefined}
    >
      <span className="w-40 shrink-0 truncate text-sm" title={sub.allocationName}>
        {sub.allocationName}
      </span>
      <div className="min-w-0 flex-1">
        <ResponsiveContainer width="100%" height={30}>
          <BarChart layout="vertical" data={data} margin={{ top: 4, right: 8, bottom: 4, left: 0 }}>
            <XAxis type="number" domain={[0, domainMax]} hide />
            <YAxis type="category" dataKey="name" hide />
            <Tooltip cursor={false} content={<GraphTooltip />} />
            <Bar dataKey="inUse" barSize={14} isAnimationActive={false} background={{ fill: TRACK }}>
              <Cell fill={overused ? BAR_OVERUSED : BAR_NORMAL} />
            </Bar>
            {/* Blue size marker, red burst marker (CueGUI parity). */}
            <ReferenceLine x={size} stroke={SIZE_MARKER} strokeWidth={2} />
            <ReferenceLine x={burst} stroke={BURST_MARKER} strokeWidth={2} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

// One show's section: a show-name label followed by one bar per subscription.
export function ShowSubscriptionGraph({
  showName,
  subscriptions,
  onSubContextMenu,
}: {
  showName: string;
  subscriptions: Subscription[] | null;
  onSubContextMenu?: (e: React.MouseEvent, sub: Subscription) => void;
}) {
  const sorted = React.useMemo(
    () => (subscriptions ? [...subscriptions].sort((a, b) => a.allocationName.localeCompare(b.allocationName)) : null),
    [subscriptions],
  );

  return (
    <section className="mb-6">
      <h2 className="mb-2 text-sm font-medium">{showName}</h2>
      {sorted === null ? (
        <div className="space-y-2">
          <Skeleton className="h-7 w-full" />
          <Skeleton className="h-7 w-full" />
        </div>
      ) : sorted.length === 0 ? (
        <p className="px-1 text-sm text-muted-foreground">This show has no subscriptions.</p>
      ) : (
        <div className="space-y-0.5">
          {sorted.map((sub) => (
            <SubscriptionBar key={sub.id || sub.name} sub={sub} onContextMenu={onSubContextMenu} />
          ))}
        </div>
      )}
    </section>
  );
}
