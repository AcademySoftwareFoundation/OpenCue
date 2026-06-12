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

/**
 * Visual frame-range selector. Web adaptation of CueGUI's
 * `cuegui/cuegui/FrameRangeSelection.py`: a horizontal strip where every
 * frame is one cell, colored by its state, laid out in ascending frame
 * order. The user click-drags across the strip to select a contiguous run
 * of frames, or shift-clicks to extend the current selection to the clicked
 * cell. The selected subset feeds straight into the same Retry / Eat / Kill
 * actions the row context menu uses (retryFrames / eatFrames / killFrames),
 * so the action wiring is shared, not duplicated.
 *
 * Accessibility note: the strip itself is a pointer affordance (one cell per
 * frame would otherwise create thousands of tab stops). Keyboard / AT users
 * keep the per-row context menu in the table for the same Retry/Eat/Kill
 * actions; once a selection exists here the action buttons below the strip
 * are fully keyboard reachable.
 */

import * as React from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import { MdOutlineCancel } from "react-icons/md";
import { TbPacman, TbReload } from "react-icons/tb";

import type { Frame } from "@/app/frames/frame-columns";
import { eatFrames, killFrames, retryFrames } from "@/app/utils/action_utils";
import { useDisableJobInteraction } from "@/app/utils/use_disable_job_interaction";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";

// Frame state -> solid swatch color. Mirrors the hues in
// components/ui/status.tsx but as filled cells so the strip reads like a
// heatmap of the job's frames. Unknown / EATEN-but-unlisted states fall
// back to a neutral gray.
const STATE_CELL_COLOR: Record<string, string> = {
  SUCCEEDED: "bg-green-500",
  FINISHED: "bg-green-500",
  RUNNING: "bg-yellow-400",
  WAITING: "bg-blue-400",
  PAUSED: "bg-blue-300",
  DEPEND: "bg-purple-400",
  DEPENDENCY: "bg-purple-400",
  DEAD: "bg-red-500",
  FAILING: "bg-red-500",
  EATEN: "bg-orange-400",
};
const DEFAULT_CELL_COLOR = "bg-gray-300 dark:bg-gray-600";

function cellColor(state: string): string {
  return STATE_CELL_COLOR[(state ?? "").toUpperCase()] ?? DEFAULT_CELL_COLOR;
}

type PendingAction = "retry" | "eat" | "kill";

const ACTION_LABEL: Record<PendingAction, string> = {
  retry: "Retry",
  eat: "Eat",
  kill: "Kill",
};

export interface FrameRangeSelectorProps {
  // Frames currently shown in the table (already state-filtered upstream by
  // SimpleDataTable). The strip mirrors exactly what the user sees.
  frames: Frame[];
  username: string;
  // Notified whenever the selected subset changes, so a parent can mirror
  // the selection elsewhere (e.g. highlight the matching table rows).
  onSelectionChange?: (frames: Frame[]) => void;
}

export function FrameRangeSelector({ frames, username, onSelectionChange }: FrameRangeSelectorProps) {
  const [collapsed, setCollapsed] = React.useState(false);
  const [selectedIds, setSelectedIds] = React.useState<Set<string>>(() => new Set());
  // Anchor for shift-click extend and drag origin, tracked by frame id so it
  // survives the 5s poll re-creating the frames array.
  const [anchorId, setAnchorId] = React.useState<string | null>(null);
  const draggingRef = React.useRef(false);
  const [pending, setPending] = React.useState<PendingAction | null>(null);

  const { disabled: jobInteractionDisabled } = useDisableJobInteraction();

  // Stable display order: ascending frame number, then layer name so
  // same-numbered frames from different layers sit next to each other.
  const displayFrames = React.useMemo(
    () => [...frames].sort((a, b) => a.number - b.number || a.layerName.localeCompare(b.layerName)),
    [frames],
  );

  // Prune ids that no longer exist (frames removed by a poll) so the count +
  // readout stay accurate. We deliberately do NOT clear the whole selection
  // on every refresh - that would wipe an in-progress selection every 5s.
  React.useEffect(() => {
    setSelectedIds((prev) => {
      if (prev.size === 0) return prev;
      const present = new Set(displayFrames.map((f) => f.id));
      let changed = false;
      const next = new Set<string>();
      prev.forEach((id) => {
        if (present.has(id)) next.add(id);
        else changed = true;
      });
      return changed ? next : prev;
    });
  }, [displayFrames]);

  const selectedFrames = React.useMemo(
    () => displayFrames.filter((f) => selectedIds.has(f.id)),
    [displayFrames, selectedIds],
  );

  // Notify the parent without making onSelectionChange a render dependency
  // (callers commonly pass an inline arrow).
  const onSelectionChangeRef = React.useRef(onSelectionChange);
  React.useEffect(() => {
    onSelectionChangeRef.current = onSelectionChange;
  });
  React.useEffect(() => {
    onSelectionChangeRef.current?.(selectedFrames);
  }, [selectedFrames]);

  // Finalize any drag on a global mouseup so releasing the button outside
  // the strip still ends the drag.
  React.useEffect(() => {
    const stop = () => {
      draggingRef.current = false;
    };
    window.addEventListener("mouseup", stop);
    return () => window.removeEventListener("mouseup", stop);
  }, []);

  const selectRange = React.useCallback(
    (a: number, b: number) => {
      const lo = Math.min(a, b);
      const hi = Math.max(a, b);
      const ids = new Set<string>();
      for (let i = lo; i <= hi; i++) {
        const frame = displayFrames[i];
        if (frame) ids.add(frame.id);
      }
      setSelectedIds(ids);
    },
    [displayFrames],
  );

  const handleMouseDown = React.useCallback(
    (index: number, shiftKey: boolean) => {
      const anchorIndex = anchorId ? displayFrames.findIndex((f) => f.id === anchorId) : -1;
      if (shiftKey && anchorIndex >= 0) {
        // Shift-click extends from the existing anchor; no drag is started.
        selectRange(anchorIndex, index);
        return;
      }
      // Fresh selection: this cell becomes the new anchor and the drag origin.
      setAnchorId(displayFrames[index].id);
      draggingRef.current = true;
      selectRange(index, index);
    },
    [anchorId, displayFrames, selectRange],
  );

  const handleMouseEnter = React.useCallback(
    (index: number) => {
      if (!draggingRef.current) return;
      const anchorIndex = anchorId ? displayFrames.findIndex((f) => f.id === anchorId) : index;
      selectRange(anchorIndex, index);
    },
    [anchorId, displayFrames, selectRange],
  );

  const clearSelection = React.useCallback(() => {
    setSelectedIds(new Set());
    setAnchorId(null);
  }, []);

  // Selected-range readout: min/max frame number across the subset (the
  // subset can span layers, so it isn't necessarily a single contiguous run
  // of numbers - the readout reflects the actual endpoints).
  const readout = React.useMemo(() => {
    if (selectedFrames.length === 0) return null;
    let min = Infinity;
    let max = -Infinity;
    for (const f of selectedFrames) {
      if (f.number < min) min = f.number;
      if (f.number > max) max = f.number;
    }
    return { min, max };
  }, [selectedFrames]);

  async function runPending() {
    if (!pending) return;
    const targets = selectedFrames;
    if (targets.length === 0) return;
    if (pending === "retry") {
      await retryFrames(targets);
    } else if (pending === "eat") {
      await eatFrames(targets);
    } else if (pending === "kill") {
      const reason = `Manual frame kill request in Cueweb's frame range selector by ${username}`;
      await killFrames(targets, username, reason);
    }
    clearSelection();
  }

  if (displayFrames.length === 0) return null;

  const hasSelection = selectedFrames.length > 0;
  const actionsDisabled = jobInteractionDisabled || !hasSelection;
  const firstNumber = displayFrames[0].number;
  const lastNumber = displayFrames[displayFrames.length - 1].number;

  return (
    <div className="mb-2 rounded-md border border-border bg-muted/30">
      <div className="flex flex-wrap items-center justify-between gap-2 px-2 py-1.5">
        <button
          type="button"
          onClick={() => setCollapsed((c) => !c)}
          aria-expanded={!collapsed}
          className="inline-flex items-center gap-1 text-xs font-medium text-foreground"
          title={collapsed ? "Show the frame range selector" : "Hide the frame range selector"}
        >
          {collapsed ? (
            <ChevronRight className="h-3.5 w-3.5" aria-hidden="true" />
          ) : (
            <ChevronDown className="h-3.5 w-3.5" aria-hidden="true" />
          )}
          <span>Frame Range Selection</span>
        </button>
        <span className="text-xs text-muted-foreground tabular-nums">
          {hasSelection && readout
            ? `Selected ${selectedFrames.length} frame${selectedFrames.length === 1 ? "" : "s"} (#${readout.min}–#${readout.max})`
            : `Drag to select a range of ${displayFrames.length} frame${displayFrames.length === 1 ? "" : "s"}`}
        </span>
      </div>

      {!collapsed && (
        <div className="px-2 pb-2">
          <div
            role="group"
            aria-label="Frame range selection strip"
            className="flex h-6 w-full select-none overflow-x-auto rounded border border-border"
          >
            {displayFrames.map((f, i) => {
              const selected = selectedIds.has(f.id);
              return (
                <div
                  key={f.id}
                  data-frame-number={f.number}
                  title={`#${f.number} ${f.layerName} — ${f.state}`}
                  onMouseDown={(e) => {
                    // Suppress the native text/drag selection so a drag across
                    // the strip reads as a range pick, not a text highlight.
                    e.preventDefault();
                    handleMouseDown(i, e.shiftKey);
                  }}
                  onMouseEnter={() => handleMouseEnter(i)}
                  className={`h-full min-w-[6px] flex-1 cursor-pointer ${cellColor(f.state)} ${
                    selected
                      ? "opacity-100 ring-1 ring-inset ring-foreground"
                      : hasSelection
                        ? "opacity-30"
                        : "opacity-90"
                  }`}
                />
              );
            })}
          </div>

          <div className="mt-1 flex justify-between text-[10px] text-muted-foreground tabular-nums">
            <span>#{firstNumber}</span>
            <span>#{lastNumber}</span>
          </div>

          <div className="mt-2 flex flex-wrap items-center gap-2">
            <Button size="xs" variant="outline" disabled={actionsDisabled} onClick={() => setPending("retry")}>
              <TbReload className="mr-1 h-3.5 w-3.5" aria-hidden="true" />
              Retry
            </Button>
            <Button size="xs" variant="outline" disabled={actionsDisabled} onClick={() => setPending("eat")}>
              <TbPacman className="mr-1 h-3.5 w-3.5" aria-hidden="true" />
              Eat
            </Button>
            <Button size="xs" variant="outline" disabled={actionsDisabled} onClick={() => setPending("kill")}>
              <MdOutlineCancel className="mr-1 h-3.5 w-3.5" aria-hidden="true" />
              Kill
            </Button>
            <Button size="xs" variant="ghost" disabled={!hasSelection} onClick={clearSelection}>
              Clear
            </Button>
          </div>
        </div>
      )}

      <ConfirmDialog
        open={pending !== null}
        onOpenChange={(o) => {
          if (!o) setPending(null);
        }}
        title={
          pending
            ? `${ACTION_LABEL[pending]} ${selectedFrames.length} frame${selectedFrames.length === 1 ? "" : "s"}?`
            : ""
        }
        description={
          pending && readout
            ? `This will ${pending} ${selectedFrames.length} frame${selectedFrames.length === 1 ? "" : "s"} in the range #${readout.min}–#${readout.max}.`
            : undefined
        }
        variant={pending === "kill" ? "destructive" : "default"}
        confirmLabel={pending ? ACTION_LABEL[pending] : "Confirm"}
        onConfirm={runPending}
      />
    </div>
  );
}
