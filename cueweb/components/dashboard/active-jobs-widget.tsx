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

import { Job } from "@/app/jobs/columns";
import { getJobs } from "@/app/utils/get_utils";
import {
  WidgetCard,
  WidgetCardError,
  WidgetCardSkeleton,
} from "@/components/dashboard/widget-card";
import { ListChecks } from "lucide-react";
import * as React from "react";

const REFRESH_MS = 15000;

export function ActiveJobsWidget() {
  const [jobs, setJobs] = React.useState<Job[] | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    let cancelled = false;
    // Serialize polls: a slow getJobs() must not be overtaken by a newer
    // tick that would overwrite fresher state with stale data.
    let inFlight = false;
    const load = async () => {
      if (inFlight) return;
      inFlight = true;
      try {
        // include_finished:false matches the default "active jobs" view used
        // by CueGUI's monitor (cuegui.JobMonitor.getJobs without a finished tag).
        const body = JSON.stringify({ r: { include_finished: false } });
        const data = await getJobs(body);
        if (!cancelled) {
          setJobs(data);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : String(err));
          // Leave any prior data in place so a transient blip does not blank the card.
        }
      } finally {
        inFlight = false;
      }
    };
    load();
    const interval = setInterval(load, REFRESH_MS);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  if (jobs === null && !error) {
    return <WidgetCardSkeleton title="Active Jobs" />;
  }
  if (jobs === null && error) {
    return (
      <WidgetCardError
        title="Active Jobs"
        href="/"
        message="Could not load jobs from Cuebot."
      />
    );
  }

  const list = jobs ?? [];
  const running = list.filter((j) => (j.jobStats?.runningFrames ?? 0) > 0).length;
  const paused = list.filter((j) => j.isPaused).length;

  return (
    <WidgetCard
      title="Active Jobs"
      icon={<ListChecks className="h-4 w-4" />}
      value={list.length}
      subLabel={`${running} running - ${paused} paused`}
      footer={
        list.length === 0
          ? "No active jobs right now."
          : `Highest priority: ${Math.max(...list.map((j) => j.priority ?? 0))}`
      }
      href="/"
      ctaLabel="View all jobs"
    />
  );
}
