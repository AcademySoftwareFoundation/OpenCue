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
import { fetchJobDepends } from "@/app/utils/action_utils";

/**
 * "View Dependencies" dialog. Mounted once at the page level and opened
 * in response to a `cueweb:open-view-dependencies` CustomEvent dispatched
 * from the row context menu. Mirrors CueGUI's DependDialog: shows the
 * job's depend list as a Type / Target / Active / OnJob / OnLayer /
 * OnFrame table.
 */

export const OPEN_VIEW_DEPENDENCIES_EVENT = "cueweb:open-view-dependencies";

export type OpenViewDependenciesDetail = {
  job: Job;
};

// The Cuebot REST gateway emits camelCase field names (e.g. proto
// `depend_on_job` -> JSON `dependOnJob`). We accept both shapes via the
// accessor helpers below so the dialog stays robust to gateway-side
// marshaller config changes.
type DependRow = {
  id?: string;
  type?: string;
  target?: string;
  active?: boolean;
  dependErJob?: string;
  dependErLayer?: string;
  dependErFrame?: string;
  dependOnJob?: string;
  dependOnLayer?: string;
  dependOnFrame?: string;
  // Fallback snake_case aliases for older gateway builds.
  depend_er_job?: string;
  depend_er_layer?: string;
  depend_er_frame?: string;
  depend_on_job?: string;
  depend_on_layer?: string;
  depend_on_frame?: string;
};

const onJobOf = (d: DependRow) => d.dependOnJob ?? d.depend_on_job ?? "";
const onLayerOf = (d: DependRow) => d.dependOnLayer ?? d.depend_on_layer ?? "";
const onFrameOf = (d: DependRow) => d.dependOnFrame ?? d.depend_on_frame ?? "";

export function ViewDependenciesDialog() {
  const [open, setOpen] = React.useState(false);
  const [job, setJob] = React.useState<Job | null>(null);
  const [depends, setDepends] = React.useState<DependRow[]>([]);
  const [loading, setLoading] = React.useState(false);

  const loadDepends = React.useCallback(async (j: Job) => {
    setLoading(true);
    try {
      const list = await fetchJobDepends(j);
      setDepends(list as DependRow[]);
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    function handler(e: Event) {
      const detail = (e as CustomEvent<OpenViewDependenciesDetail>).detail;
      if (!detail?.job) return;
      setJob(detail.job);
      setDepends([]);
      setOpen(true);
      loadDepends(detail.job);
    }
    window.addEventListener(OPEN_VIEW_DEPENDENCIES_EVENT, handler);
    return () =>
      window.removeEventListener(OPEN_VIEW_DEPENDENCIES_EVENT, handler);
  }, [loadDepends]);

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="sm:max-w-4xl">
        <DialogHeader>
          <DialogTitle>
            <span className="font-mono break-all">
              Dependencies for Job: {job?.name ?? ""}
            </span>
          </DialogTitle>
          <DialogDescription>
            Each row is a depend.Depend on this job. Type names match
            depend.DependType (e.g. JOB_ON_JOB, LAYER_ON_FRAME), Target is
            INTERNAL or EXTERNAL, Active indicates whether the depend is
            still blocking the dependent. Empty OnLayer / OnFrame is
            normal for job-level depends.
          </DialogDescription>
        </DialogHeader>

        <div className="max-h-[55vh] overflow-auto rounded-md border border-input text-xs">
          <table className="w-full table-auto">
            <thead className="bg-foreground/[0.04] sticky top-0">
              <tr className="text-left">
                <th className="px-3 py-2">Type</th>
                <th className="px-3 py-2">Target</th>
                <th className="px-3 py-2">Active</th>
                <th className="px-3 py-2">OnJob</th>
                <th className="px-3 py-2">OnLayer</th>
                <th className="px-3 py-2">OnFrame</th>
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr>
                  <td colSpan={6} className="px-3 py-4 text-center text-foreground/60">
                    Loading dependencies...
                  </td>
                </tr>
              )}
              {!loading && depends.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-3 py-4 text-center text-foreground/60">
                    No dependencies on this job.
                  </td>
                </tr>
              )}
              {!loading && depends.map((d, i) => (
                <tr key={d.id ?? i} className="border-t border-input/60">
                  <td className="px-3 py-1.5 font-mono">{d.type ?? ""}</td>
                  <td className="px-3 py-1.5 font-mono">{d.target ?? ""}</td>
                  <td className="px-3 py-1.5 font-mono">{d.active === undefined ? "" : String(d.active)}</td>
                  <td className="px-3 py-1.5 font-mono break-all">{onJobOf(d)}</td>
                  <td className="px-3 py-1.5 font-mono break-all">{onLayerOf(d)}</td>
                  <td className="px-3 py-1.5 font-mono break-all">{onFrameOf(d)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            onClick={() => job && loadDepends(job)}
            disabled={loading || !job}
          >
            Refresh
          </Button>
          <Button type="button" onClick={() => setOpen(false)}>
            Close
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
