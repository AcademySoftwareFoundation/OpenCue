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
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import type { Job } from "@/app/jobs/columns";
import { setJobPriority } from "@/app/utils/action_utils";

/**
 * "Set Priority" dialog. Mounted once at the page level and opened in
 * response to a `cueweb:open-set-priority` CustomEvent dispatched from
 * the row context menu. Decoupled this way so the menu's free-function
 * handlers can stay free of component refs / table-state plumbing.
 *
 * UI: a 1-100 range slider tied to a number input. Either control can
 * drive the value; both stay in sync. Apply calls the existing
 * setJobPriority action (which proxies to /job.JobInterface/SetPriority
 * via /api/job/action/setpriority) and then dispatches a
 * `cueweb:priority-changed` window event so the Jobs table can
 * optimistically refresh the row without waiting for the next 5s poll.
 */

export const OPEN_SET_PRIORITY_EVENT = "cueweb:open-set-priority";
// Fired after a successful priority change so any open Jobs table
// (Cuetopia) can update its row immediately.
export const PRIORITY_CHANGED_EVENT = "cueweb:priority-changed";

export type OpenSetPriorityDetail = {
  job: Job;
};

export type PriorityChangedDetail = {
  jobId: string;
  priority: number;
};

const MIN = 1;
const MAX = 100;
const DEFAULT_PRIORITY = 100;

function clamp(n: number): number {
  return Math.min(MAX, Math.max(MIN, Math.round(n)));
}

export function SetPriorityDialog() {
  const [open, setOpen] = React.useState(false);
  const [job, setJob] = React.useState<Job | null>(null);
  const [value, setValue] = React.useState<number>(DEFAULT_PRIORITY);
  const [submitting, setSubmitting] = React.useState(false);

  React.useEffect(() => {
    function handler(e: Event) {
      const detail = (e as CustomEvent<OpenSetPriorityDetail>).detail;
      if (!detail?.job) return;
      setJob(detail.job);
      const current = Number(detail.job.priority);
      setValue(
        Number.isFinite(current) && current >= MIN && current <= MAX
          ? Math.round(current)
          : DEFAULT_PRIORITY,
      );
      setOpen(true);
    }
    window.addEventListener(OPEN_SET_PRIORITY_EVENT, handler);
    return () => window.removeEventListener(OPEN_SET_PRIORITY_EVENT, handler);
  }, []);

  async function handleApply() {
    if (!job) return;
    setSubmitting(true);
    try {
      await setJobPriority(job, value);
      window.dispatchEvent(
        new CustomEvent<PriorityChangedDetail>(PRIORITY_CHANGED_EVENT, {
          detail: { jobId: job.id, priority: value },
        }),
      );
      setOpen(false);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={submitting ? () => {} : setOpen}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Set Priority</DialogTitle>
          <DialogDescription>
            {job ? (
              <>
                <span className="font-mono break-all">{job.name}</span>
                <br />
                Higher numbers dispatch first. Range 1-100, default 100.
              </>
            ) : (
              "Higher numbers dispatch first. Range 1-100."
            )}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          <div className="flex items-center gap-3">
            <input
              type="range"
              min={MIN}
              max={MAX}
              step={1}
              value={value}
              onChange={(e) => setValue(clamp(Number(e.target.value)))}
              disabled={submitting}
              aria-label="Priority slider"
              className="flex-1 accent-foreground/80"
            />
            <input
              type="number"
              min={MIN}
              max={MAX}
              step={1}
              value={value}
              onChange={(e) => {
                const n = Number(e.target.value);
                if (Number.isFinite(n)) setValue(clamp(n));
              }}
              disabled={submitting}
              aria-label="Priority value"
              className="w-20 rounded-md border border-input bg-background px-3 py-1.5 text-sm text-center font-mono"
            />
          </div>
          <div className="flex justify-between text-xs text-foreground/60">
            <span>{MIN} (lowest)</span>
            <span>{MAX} (highest)</span>
          </div>
        </div>

        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            onClick={() => setOpen(false)}
            disabled={submitting}
          >
            Cancel
          </Button>
          <Button type="button" onClick={handleApply} disabled={submitting}>
            {submitting ? "Applying…" : "Apply"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
