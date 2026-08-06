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

import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import * as React from "react";

/**
 * Presentational shell for a chart card. Matches the visual language of
 * WidgetCard so the dashboard stays consistent: rounded card with a small
 * uppercase title, optional subtitle, optional top-right icon, and a fixed
 * chart area below.
 *
 * Charts manage their own data fetching + skeleton states; this shell just
 * owns layout and the title row. Pass `loading` to swap the chart body for a
 * matched-height skeleton, and `error` to show a destructive-themed message
 * without unmounting the title.
 */
export interface ChartCardProps {
  title: string;
  subtitle?: React.ReactNode;
  icon?: React.ReactNode;
  /** Fixed chart-area height in Tailwind utility (`h-64`, `h-72`, ...). */
  bodyHeightClass?: string;
  loading?: boolean;
  error?: string | null;
  /** Footer slot - typically a small legend or "click a bar to..." hint. */
  footer?: React.ReactNode;
  className?: string;
  children: React.ReactNode;
}

export function ChartCard({
  title,
  subtitle,
  icon,
  bodyHeightClass = "h-64",
  loading = false,
  error = null,
  footer,
  className,
  children,
}: ChartCardProps) {
  return (
    <section
      className={cn(
        "flex h-full flex-col rounded-xl border border-border bg-card p-4 shadow-sm",
        className,
      )}
      aria-busy={loading || undefined}
    >
      <header className="flex items-start justify-between gap-2">
        <div>
          <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            {title}
          </h2>
          {subtitle ? (
            <p className="mt-1 text-xs text-muted-foreground">{subtitle}</p>
          ) : null}
        </div>
        {icon ? (
          <span className="text-muted-foreground" aria-hidden="true">
            {icon}
          </span>
        ) : null}
      </header>

      <div className={cn("relative mt-3", bodyHeightClass)}>
        {loading ? (
          <Skeleton className="absolute inset-0 rounded-md" />
        ) : error ? (
          <div className="absolute inset-0 flex items-center justify-center rounded-md border border-destructive/30 bg-destructive/5 p-4 text-center text-sm text-destructive">
            {error}
          </div>
        ) : (
          // Chart.js sizes to the parent box, so we wrap in a flex container
          // that fills the fixed-height slot above.
          <div className="absolute inset-0">{children}</div>
        )}
      </div>

      {footer ? (
        <div className="mt-3 text-xs text-muted-foreground">{footer}</div>
      ) : null}
    </section>
  );
}

/**
 * Theme-aware palette token resolution. Reads the CSS variables that
 * shadcn / tailwind populate on the document root so chart colors track
 * light/dark mode without a hard-coded second palette.
 *
 * Falls back to safe defaults when running on the server (variables not
 * available until first paint).
 */
export function useChartColors(): {
  text: string;
  mutedText: string;
  grid: string;
  series: string[];
  destructive: string;
  warning: string;
  success: string;
} {
  const [colors, setColors] = React.useState(() => fallbackColors());

  React.useEffect(() => {
    const read = () => setColors(readColors());
    read();

    // Re-read when the theme class on <html> changes (next-themes toggles a
    // `class="dark"` attribute).
    const observer = new MutationObserver(read);
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["class", "style"],
    });
    return () => observer.disconnect();
  }, []);

  return colors;
}

function fallbackColors() {
  return {
    text: "#0f172a",
    mutedText: "#64748b",
    grid: "rgba(148, 163, 184, 0.25)",
    series: SERIES_PALETTE,
    destructive: "#ef4444",
    warning: "#f59e0b",
    success: "#10b981",
  };
}

function readColors() {
  if (typeof window === "undefined") return fallbackColors();
  const style = getComputedStyle(document.documentElement);
  const cssVar = (name: string, fallback: string) => {
    const value = style.getPropertyValue(name).trim();
    return value ? `hsl(${value})` : fallback;
  };
  return {
    text: cssVar("--foreground", "#0f172a"),
    mutedText: cssVar("--muted-foreground", "#64748b"),
    grid: cssVar("--border", "rgba(148, 163, 184, 0.25)"),
    series: SERIES_PALETTE,
    destructive: cssVar("--destructive", "#ef4444"),
    warning: "#f59e0b",
    success: "#10b981",
  };
}

// Stable categorical palette. Chosen for contrast against both light and
// dark card backgrounds; reused across all charts so a color always means
// the same axis when reading multiple charts together is useful.
const SERIES_PALETTE = [
  "#2563eb", // blue-600
  "#10b981", // emerald-500
  "#f59e0b", // amber-500
  "#ef4444", // red-500
  "#a855f7", // purple-500
  "#06b6d4", // cyan-500
  "#84cc16", // lime-500
  "#f97316", // orange-500
  "#ec4899", // pink-500
  "#14b8a6", // teal-500
];

/**
 * Standard frame-state color mapping. Reused across charts that surface
 * frame breakdowns so the same color always represents the same state.
 * Aligned with cuegui's per-state coloring in `cuegui/cuegui/Constants.py`.
 */
export const FRAME_STATE_COLORS: Record<string, string> = {
  Running: "#2563eb",   // blue
  Waiting: "#94a3b8",   // slate
  Succeeded: "#10b981", // emerald
  Dead: "#ef4444",      // red
  Eaten: "#f97316",     // orange
  Depend: "#a855f7",    // purple
  Pending: "#f59e0b",   // amber
};
