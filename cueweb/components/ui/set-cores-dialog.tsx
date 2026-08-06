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
import { setJobCores } from "@/app/utils/action_utils";

/**
 * "Set Min/Max Cores" dialog (#2281). Mounted once at the page level and
 * opened in response to a `cueweb:open-set-cores` CustomEvent from the row
 * context menu. Two number inputs, client-side min<=max guard. Apply calls
 * setJobCores (which POSTs SetMinCores + SetMaxCores) then dispatches
 * `cueweb:cores-changed` so the Jobs table can optimistically refresh.
 *
 * Range 0-50000 mirrors CueGUI's setMinCores/setMaxCores QInputDialog.
 */

export const OPEN_SET_CORES_EVENT = "cueweb:open-set-cores";
export const CORES_CHANGED_EVENT = "cueweb:cores-changed";

export type OpenSetCoresDetail = {
  job: Job;
};

export type CoresChangedDetail = {
  jobId: string;
  minCores: number;
  maxCores: number;
};

const MIN = 0;
const MAX = 50000;

function clampCores(n: number): number {
  if (!Number.isFinite(n)) return MIN;
  return Math.min(MAX, Math.max(MIN, n));
}

export function SetCoresDialog() {
  const [open, setOpen] = React.useState(false);
  const [job, setJob] = React.useState<Job | null>(null);
  const [minCores, setMinCores] = React.useState<number>(0);
  const [maxCores, setMaxCores] = React.useState<number>(0);
  const [submitting, setSubmitting] = React.useState(false);

  React.useEffect(() => {
    function handler(e: Event) {
      const detail = (e as CustomEvent<OpenSetCoresDetail>).detail;
      if (!detail?.job) return;
      setSubmitting(false);
      setJob(detail.job);
      setMinCores(clampCores(Number(detail.job.minCores)));
      setMaxCores(clampCores(Number(detail.job.maxCores)));
      setOpen(true);
    }
    window.addEventListener(OPEN_SET_CORES_EVENT, handler);
    return () => window.removeEventListener(OPEN_SET_CORES_EVENT, handler);
  }, []);

  const invalid = minCores > maxCores;

  async function handleApply() {
    if (!job || invalid) return;
    setSubmitting(true);
    try {
      const ok = await setJobCores(job, minCores, maxCores);
      // Only patch the row optimistically when the action actually succeeded;
      // setJobCores surfaces failures via a toast and returns false, so a
      // rejected change leaves the table at its true value instead of flickering.
      if (ok) {
        window.dispatchEvent(
          new CustomEvent<CoresChangedDetail>(CORES_CHANGED_EVENT, {
            detail: { jobId: job.id, minCores, maxCores },
          }),
        );
        setOpen(false);
      }
    } catch (error) {
      console.error("Failed to set cores:", error);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={submitting ? () => {} : setOpen}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Set Min/Max Cores</DialogTitle>
          <DialogDescription>
            {job ? (
              <>
                <span className="font-mono break-all">{job.name}</span>
                <br />
                Minimum and maximum cores Cuebot may book for this job. Range 0-50000.
              </>
            ) : (
              "Minimum and maximum cores. Range 0-50000."
            )}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          <div className="flex items-center gap-4">
            <label className="flex flex-1 flex-col gap-1 text-sm">
              <span className="text-foreground/70">Min Cores</span>
              <input
                type="number"
                min={MIN}
                max={MAX}
                step={1}
                value={minCores}
                onChange={(e) => setMinCores(clampCores(Number(e.target.value)))}
                disabled={submitting}
                aria-label="Minimum cores"
                className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-sm font-mono"
              />
            </label>
            <label className="flex flex-1 flex-col gap-1 text-sm">
              <span className="text-foreground/70">Max Cores</span>
              <input
                type="number"
                min={MIN}
                max={MAX}
                step={1}
                value={maxCores}
                onChange={(e) => setMaxCores(clampCores(Number(e.target.value)))}
                disabled={submitting}
                aria-label="Maximum cores"
                className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-sm font-mono"
              />
            </label>
          </div>
          {invalid && (
            <p className="text-xs text-destructive">
              Min cores must be less than or equal to max cores.
            </p>
          )}
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
          <Button type="button" onClick={handleApply} disabled={submitting || invalid}>
            {submitting ? "Applying…" : "Apply"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
