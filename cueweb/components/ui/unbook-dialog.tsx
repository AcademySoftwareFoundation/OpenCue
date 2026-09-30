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
import { Checkbox } from "@/components/ui/checkbox";
import type { Job } from "@/app/jobs/columns";
import { unbookJob } from "@/app/utils/action_utils";

/**
 * "Unbook" dialog (#2288). Mounted once at the page level, opened by a
 * `cueweb:open-unbook` CustomEvent from the row context menu. Job-scoped MVP:
 * unbooks every proc the job holds, with an optional "Kill unbooked frames?"
 * checkbox. When kill is checked, Apply moves to a second confirmation phase
 * (CueGUI KillConfirmationDialog parity) before sending. On success it
 * dispatches `cueweb:refresh-now` so the table reflects the freed procs.
 */

export const OPEN_UNBOOK_EVENT = "cueweb:open-unbook";

export type OpenUnbookDetail = {
  job: Job;
};

const KILL_WARNING =
  "Unbook and kill the matching running frame(s)? Killed frames stop immediately and lose their progress.";

export function UnbookDialog() {
  const [open, setOpen] = React.useState(false);
  const [job, setJob] = React.useState<Job | null>(null);
  const [kill, setKill] = React.useState(false);
  const [confirmingKill, setConfirmingKill] = React.useState(false);
  const [submitting, setSubmitting] = React.useState(false);

  React.useEffect(() => {
    function handler(e: Event) {
      const detail = (e as CustomEvent<OpenUnbookDetail>).detail;
      if (!detail?.job) return;
      setJob(detail.job);
      setKill(false);
      setConfirmingKill(false);
      setSubmitting(false);
      setOpen(true);
    }
    window.addEventListener(OPEN_UNBOOK_EVENT, handler);
    return () => window.removeEventListener(OPEN_UNBOOK_EVENT, handler);
  }, []);

  async function doUnbook() {
    if (!job) return;
    setSubmitting(true);
    try {
      const ok = await unbookJob(job, kill);
      // Only refresh the table when the unbook actually succeeded; unbookJob
      // surfaces failures via a toast and returns false.
      if (ok) {
        window.dispatchEvent(new CustomEvent("cueweb:refresh-now"));
        setOpen(false);
      }
    } catch (error) {
      console.error("Failed to unbook:", error);
    } finally {
      setSubmitting(false);
    }
  }

  function handlePrimary() {
    if (kill && !confirmingKill) {
      setConfirmingKill(true);
      return;
    }
    void doUnbook();
  }

  return (
    <Dialog open={open} onOpenChange={submitting ? () => {} : setOpen}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{confirmingKill ? "Unbook and kill frames?" : "Unbook job"}</DialogTitle>
          <DialogDescription>
            {confirmingKill ? (
              <span className="block text-destructive">{KILL_WARNING}</span>
            ) : job ? (
              <>
                Unbook every proc this job currently holds.
                <br />
                <span className="font-mono break-all">{job.name}</span>
              </>
            ) : (
              "Unbook every proc this job currently holds."
            )}
          </DialogDescription>
        </DialogHeader>

        {!confirmingKill && (
          <div className="py-2">
            <label className="flex items-center gap-2 text-sm">
              <Checkbox
                checked={kill}
                onCheckedChange={(checked) => setKill(checked === true)}
                disabled={submitting}
                aria-label="Kill unbooked frames"
              />
              Kill unbooked frames?
            </label>
          </div>
        )}

        <DialogFooter>
          {confirmingKill ? (
            <Button
              type="button"
              variant="outline"
              onClick={() => { if (!submitting) setConfirmingKill(false); }}
              disabled={submitting}
            >
              Back
            </Button>
          ) : (
            <Button
              type="button"
              variant="outline"
              onClick={() => setOpen(false)}
              disabled={submitting}
            >
              Cancel
            </Button>
          )}
          <Button
            type="button"
            variant={kill ? "destructive" : "default"}
            onClick={handlePrimary}
            disabled={submitting}
          >
            {submitting
              ? "Unbooking…"
              : confirmingKill
                ? "Unbook & Kill"
                : kill
                  ? "Continue"
                  : "Unbook"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
