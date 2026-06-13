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

import type { Frame } from "@/app/frames/frame-columns";
import type { Job } from "@/app/jobs/columns";
import { eatFrames, killFrames, retryFrames } from "@/app/utils/action_utils";
import { Button } from "@/components/ui/button";

// Visual frame-range selector (CueGUI FrameRangeSelection parity). Renders a
// state-colored strip with one tick per frame; click-drag selects a contiguous
// range and Shift-click extends from the anchor. The selected frames feed the
// existing Retry / Eat / Kill actions.

// SVG fill per frame state, mirroring cuegui's style.colors.frame_state.
const STATE_FILL: Record<string, string> = {
  SUCCEEDED: "#37c837",
  RUNNING: "#c8c837",
  WAITING: "#87cfeb",
  DEPEND: "#a020f0",
  SETUP: "#a020f0",
  DEAD: "#ff0000",
  EATEN: "#960000",
  CHECKPOINT: "#3d62f7",
};
const DEFAULT_FILL = "#9aa0a6";

function fillFor(state: string): string {
  return STATE_FILL[(state || "").toUpperCase()] ?? DEFAULT_FILL;
}

function clamp(v: number, lo: number, hi: number): number {
  return Math.max(lo, Math.min(hi, v));
}

export function FrameRangeSelector({
  frames,
  job,
  username,
}: {
  frames: Frame[];
  job?: Job;
  username: string;
}) {
  // Frames sorted by number define the strip's left-to-right order. Selection
  // is tracked as indices into this sorted list (robust to non-contiguous
  // frame numbers like 1-100x5).
  const sorted = React.useMemo(
    () => [...frames].sort((a, b) => a.number - b.number),
    [frames],
  );
  const n = sorted.length;

  const [anchor, setAnchor] = React.useState<number | null>(null);
  const [sel, setSel] = React.useState<{ a: number; b: number } | null>(null);
  const [dragging, setDragging] = React.useState(false);
  const stripRef = React.useRef<HTMLDivElement | null>(null);

  // Clear a stale selection if the frame set shrinks (job switch / refilter).
  React.useEffect(() => {
    setSel((prev) => (prev && prev.a < n && prev.b < n ? prev : null));
    setAnchor((prev) => (prev !== null && prev < n ? prev : null));
  }, [n]);

  const indexFromClientX = React.useCallback(
    (clientX: number): number => {
      const el = stripRef.current;
      if (!el || n === 0) return 0;
      const rect = el.getBoundingClientRect();
      const ratio = (clientX - rect.left) / Math.max(1, rect.width);
      return clamp(Math.floor(ratio * n), 0, n - 1);
    },
    [n],
  );

  const onPointerDown = (e: React.PointerEvent) => {
    if (n === 0) return;
    const idx = indexFromClientX(e.clientX);
    if (e.shiftKey && anchor !== null) {
      setSel({ a: anchor, b: idx });
      return;
    }
    setAnchor(idx);
    setSel({ a: idx, b: idx });
    setDragging(true);
  };

  const onPointerMove = (e: React.PointerEvent) => {
    if (!dragging || anchor === null) return;
    setSel({ a: anchor, b: indexFromClientX(e.clientX) });
  };

  // End the drag even if the pointer is released outside the strip.
  React.useEffect(() => {
    if (!dragging) return;
    const stop = () => setDragging(false);
    window.addEventListener("pointerup", stop);
    return () => window.removeEventListener("pointerup", stop);
  }, [dragging]);

  if (n === 0) return null;

  const lo = sel ? Math.min(sel.a, sel.b) : -1;
  const hi = sel ? Math.max(sel.a, sel.b) : -1;
  const selectedFrames = sel ? sorted.slice(lo, hi + 1) : [];
  const hasSelection = selectedFrames.length > 0;
  const rangeLabel = hasSelection
    ? `${sorted[lo].number}–${sorted[hi].number} (${selectedFrames.length} frame${selectedFrames.length === 1 ? "" : "s"})`
    : "none";

  const clearSelection = () => {
    setSel(null);
    setAnchor(null);
  };

  const doRetry = () => hasSelection && retryFrames(selectedFrames);
  const doEat = () => hasSelection && eatFrames(selectedFrames);
  const doKill = () =>
    hasSelection &&
    killFrames(selectedFrames, username, `Frame range kill from CueWeb selector by ${username}`);

  return (
    <div className="mb-2 rounded-md border border-border bg-muted/20 p-2">
      <div className="mb-1.5 flex flex-wrap items-center gap-2 text-xs">
        <span className="font-medium text-muted-foreground">Frame range</span>
        <span className="text-muted-foreground/80">
          Drag to select; Shift-click to extend.
        </span>
        <span className="ml-auto tabular-nums">
          Selected: <span className="font-mono">{rangeLabel}</span>
        </span>
      </div>

      {/* The strip: an SVG of per-frame ticks stretched to the container width,
          with a selection overlay positioned by percentage. */}
      <div
        ref={stripRef}
        role="slider"
        aria-label="Frame range selector"
        aria-valuemin={sorted[0].number}
        aria-valuemax={sorted[n - 1].number}
        aria-valuenow={hasSelection ? sorted[hi].number : sorted[0].number}
        className="relative h-7 w-full cursor-crosshair touch-none select-none overflow-hidden rounded border border-input bg-background"
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
      >
        <svg
          className="absolute inset-0 h-full w-full"
          viewBox={`0 0 ${n} 1`}
          preserveAspectRatio="none"
          aria-hidden="true"
        >
          {sorted.map((f, i) => (
            <rect key={f.id} x={i} y={0} width={1} height={1} fill={fillFor(f.state)} />
          ))}
        </svg>
        {hasSelection ? (
          <div
            className="pointer-events-none absolute top-0 h-full border-2 border-primary bg-primary/25"
            style={{
              left: `${(lo / n) * 100}%`,
              width: `${((hi - lo + 1) / n) * 100}%`,
            }}
            aria-hidden="true"
          />
        ) : null}
      </div>

      <div className="mt-2 flex flex-wrap items-center gap-2">
        <Button size="xs" variant="outline" onClick={doRetry} disabled={!hasSelection}>
          Retry
        </Button>
        <Button size="xs" variant="outline" onClick={doEat} disabled={!hasSelection}>
          Eat
        </Button>
        <Button
          size="xs"
          variant="outline"
          className="text-destructive hover:text-destructive"
          onClick={doKill}
          disabled={!hasSelection || !job}
        >
          Kill
        </Button>
        <Button size="xs" variant="ghost" onClick={clearSelection} disabled={!hasSelection}>
          Clear
        </Button>
      </div>
    </div>
  );
}
