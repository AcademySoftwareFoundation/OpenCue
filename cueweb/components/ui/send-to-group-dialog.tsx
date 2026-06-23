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

import type { Job } from "@/app/jobs/columns";
import { reparentJobs } from "@/app/utils/action_utils";
import { Group, getActiveShows, getShowGroups } from "@/app/utils/get_utils";
import { handleError } from "@/app/utils/notify_utils";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

// "Send To Group..." dialog (CueGUI Monitor Cue parity). Opened by the
// `cueweb:open-send-to-group` event from the job context menu. Lists the
// destination groups in the job's show and reparents the job to the chosen one.
export function SendToGroupDialog() {
  const [open, setOpen] = React.useState(false);
  const [job, setJob] = React.useState<Job | null>(null);
  const [groups, setGroups] = React.useState<Group[]>([]);
  const [selectedId, setSelectedId] = React.useState("");
  const [loading, setLoading] = React.useState(false);
  const [busy, setBusy] = React.useState(false);
  // Staleness token: if the dialog is reopened for another job before this
  // load finishes, only the latest load() may write state.
  const loadVersionRef = React.useRef(0);

  const load = React.useCallback(async (j: Job) => {
    const version = ++loadVersionRef.current;
    setLoading(true);
    setGroups([]);
    setSelectedId("");
    try {
      // Resolve the job's show id, then fetch that show's groups.
      const shows = await getActiveShows();
      if (version !== loadVersionRef.current) return;
      const show = shows.find((s) => s.name === j.show);
      if (!show) return;
      const list = await getShowGroups(show.id);
      if (version !== loadVersionRef.current) return;
      setGroups(list);
      if (list.length > 0) setSelectedId(list[0].id);
    } catch (error) {
      handleError(error, "Could not load groups");
    } finally {
      if (version === loadVersionRef.current) setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    function handler(e: Event) {
      const j = (e as CustomEvent<{ job?: Job }>).detail?.job;
      if (!j) return;
      setJob(j);
      setOpen(true);
      load(j);
    }
    window.addEventListener("cueweb:open-send-to-group", handler);
    return () => window.removeEventListener("cueweb:open-send-to-group", handler);
  }, [load]);

  async function apply() {
    if (!job || !selectedId) return;
    setBusy(true);
    try {
      const ok = await reparentJobs(selectedId, [job.id]);
      if (ok) {
        setOpen(false);
        // Nudge the table to re-fetch so the moved job reflects its new group.
        window.dispatchEvent(new CustomEvent("cueweb:refresh-now"));
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Send jobs to group</DialogTitle>
          <DialogDescription>What group should this job move to?</DialogDescription>
        </DialogHeader>
        <div className="min-w-0 space-y-3 py-2 text-sm">
          <p className="break-all font-mono text-xs text-muted-foreground">{job?.name}</p>
          {loading ? (
            <p className="text-muted-foreground">Loading groups...</p>
          ) : groups.length === 0 ? (
            <p className="text-muted-foreground">No groups found for show &ldquo;{job?.show}&rdquo;.</p>
          ) : (
            <label className="block min-w-0">
              <span className="text-muted-foreground">Group</span>
              <select
                value={selectedId}
                onChange={(e) => setSelectedId(e.target.value)}
                aria-label="Destination group"
                className="mt-1 h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              >
                {groups.map((g) => (
                  <option key={g.id} value={g.id}>
                    {`${"  ".repeat(Math.max(0, g.level))}${g.name}`}
                  </option>
                ))}
              </select>
            </label>
          )}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
          <Button onClick={apply} disabled={busy || loading || !selectedId}>OK</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
