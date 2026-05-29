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
import { AlertTriangle } from "lucide-react";
import * as React from "react";

const REFRESH_MS = 15000;
// 24h matches the task spec: "Recent Failures (last 24h)".
const FAILURE_WINDOW_SEC = 24 * 60 * 60;

export function RecentFailuresWidget() {
  const [jobs, setJobs] = React.useState<Job[] | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        // include_finished so we can still surface failures from jobs that
        // are mid-fail or recently auto-finished. CueGUI's failure surfacing
        // (cuegui.JobMonitor with `Failing`) is computed the same way -
        // a job is considered failing as soon as deadFrames > 0.
        const body = JSON.stringify({ r: { include_finished: true } });
        const data = await getJobs(body);
        if (!cancelled) {
          setJobs(data);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : String(err));
        }
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
    return <WidgetCardSkeleton title="Recent Failures" />;
  }
  if (jobs === null && error) {
    return (
      <WidgetCardError
        title="Recent Failures"
        href="/"
        message="Could not load jobs from Cuebot."
      />
    );
  }

  const now = Math.floor(Date.now() / 1000);
  const cutoff = now - FAILURE_WINDOW_SEC;

  const failing = (jobs ?? []).filter((j) => {
    const dead = j.jobStats?.deadFrames ?? 0;
    if (dead <= 0) return false;
    // Anchor recency on stopTime when set (finished failing jobs) and on
    // startTime otherwise (currently failing jobs keep startTime forever).
    const anchor = j.stopTime && j.stopTime > 0 ? j.stopTime : j.startTime;
    return anchor >= cutoff;
  });

  const totalDeadFrames = failing.reduce(
    (acc, j) => acc + (j.jobStats?.deadFrames ?? 0),
    0,
  );

  // Top 3 offenders by deadFrames - keeps the card readable.
  const top = [...failing]
    .sort((a, b) => (b.jobStats?.deadFrames ?? 0) - (a.jobStats?.deadFrames ?? 0))
    .slice(0, 3);

  return (
    <WidgetCard
      title="Recent Failures"
      icon={<AlertTriangle className="h-4 w-4" />}
      value={failing.length}
      subLabel={
        failing.length === 0
          ? "0 dead frames in the last 24h"
          : `${totalDeadFrames} dead frame${totalDeadFrames === 1 ? "" : "s"} in the last 24h`
      }
      footer={
        top.length === 0 ? (
          "No jobs with dead frames in the last 24h."
        ) : (
          <ul className="space-y-1">
            {top.map((j) => (
              <li key={j.id} className="flex items-center justify-between gap-2">
                <span className="truncate" title={j.name}>
                  {j.name}
                </span>
                <span className="text-destructive tabular-nums">
                  {j.jobStats?.deadFrames ?? 0}
                </span>
              </li>
            ))}
          </ul>
        )
      }
      href="/?failing=1"
      ctaLabel="View failing jobs"
    />
  );
}
