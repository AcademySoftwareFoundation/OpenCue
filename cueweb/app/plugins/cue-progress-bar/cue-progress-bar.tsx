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

"use client";

import * as React from "react";
import { useSession } from "next-auth/react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  openPluginSettings,
  usePluginSetting,
} from "@/components/ui/settings-dialog";
import type { Job } from "@/app/jobs/columns";
import {
  killJobs,
  pauseJobs,
  retryJobsDeadFrames,
  unpauseJobs,
} from "@/app/utils/action_utils";
import { getJob, getJobsForRegex } from "@/app/utils/get_utils";
import { UNKNOWN_USER } from "@/app/utils/constants";
import { registerSetting, type PluginComponentProps } from "@/lib/plugins";
import { cn } from "@/lib/utils";

// Settings this plugin contributes to the shared settings dialog. Registered at
// module load (the chunk only loads when /plugins/cue-progress-bar is visited),
// demonstrating the settings half of the plugin API.
const REFRESH_SETTING = registerSetting({
  key: "cue-progress-bar.refreshSeconds",
  plugin: "cue-progress-bar",
  label: "Refresh interval (seconds)",
  kind: "number",
  default: 5,
  description: "How often the progress bar polls Cuebot for updated frame counts.",
});

const DEFAULT_JOB_SETTING = registerSetting({
  key: "cue-progress-bar.defaultJob",
  plugin: "cue-progress-bar",
  label: "Default job name",
  kind: "string",
  default: "",
  description: "Job name to pre-fill when the plugin opens.",
});

/**
 * Frame states drawn in the bar, in the same order and colors as the CueGUI
 * `cueprogbar` sample (`RGB_FRAME_STATE` in
 * cuegui/cuegui/cueguiplugin/cueprogbar/main.py).
 */
const FRAME_STATES = [
  { key: "succeededFrames", label: "Succeeded", color: "rgb(55, 200, 55)" },
  { key: "runningFrames", label: "Running", color: "rgb(200, 200, 55)" },
  { key: "waitingFrames", label: "Waiting", color: "rgb(135, 207, 235)" },
  { key: "dependFrames", label: "Depend", color: "rgb(160, 32, 240)" },
  { key: "deadFrames", label: "Dead", color: "rgb(255, 0, 0)" },
  { key: "eatenFrames", label: "Eaten", color: "rgb(150, 0, 0)" },
] as const;

/** Clamp the refresh interval to a sane range (seconds). */
function clampRefreshSeconds(value: number): number {
  if (!Number.isFinite(value)) return 5;
  return Math.min(120, Math.max(2, Math.round(value)));
}

/**
 * Cue Progress Bar — a CueWeb port of the CueGUI `cueprogbar` sample plugin.
 * Enter a job name to render a live, color-coded bar of its frame-state
 * totals, with pause / unpause / kill / retry-dead controls. Polls Cuebot on
 * an interval (configurable via plugin settings), mirroring the original's
 * 5-second `UPDATE_DELAY`.
 */
export default function CueProgressBar({ manifest }: PluginComponentProps) {
  const { data: session } = useSession();
  const username = session?.user?.email ? session.user.email.split("@")[0] : UNKNOWN_USER;

  const refreshSeconds = clampRefreshSeconds(Number(usePluginSetting(REFRESH_SETTING)));
  const defaultJob = String(usePluginSetting(DEFAULT_JOB_SETTING) ?? "");

  const [nameInput, setNameInput] = React.useState("");
  const [job, setJob] = React.useState<Job | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  // Pre-fill the input from the persisted default once it hydrates.
  React.useEffect(() => {
    if (defaultJob) setNameInput((prev) => prev || defaultJob);
  }, [defaultJob]);

  // Resolve a job by name. Mirrors cueprogbar's findJob: match the exact name
  // when present, otherwise fall back to the first regex match.
  const loadJob = React.useCallback(async (name: string) => {
    const trimmed = name.trim();
    if (!trimmed) return;
    setLoading(true);
    setError(null);
    try {
      const matches = await getJobsForRegex(trimmed, true);
      const found = matches.find((j) => j.name === trimmed) ?? matches[0] ?? null;
      if (found) {
        setJob(found);
      } else {
        setJob(null);
        setError(`Unable to find job: ${trimmed}`);
      }
    } catch (err) {
      setJob(null);
      setError(err instanceof Error ? err.message : "Failed to load job");
    } finally {
      setLoading(false);
    }
  }, []);

  // Poll the resolved job for fresh frame counts until it finishes, matching
  // the original's QTimer-driven refresh.
  React.useEffect(() => {
    if (!job || job.state === "FINISHED") return;
    const id = job.id;
    const interval = window.setInterval(async () => {
      try {
        const fresh = await getJob(id);
        if (fresh) setJob(fresh);
      } catch {
        // Transient errors are surfaced on the next successful poll; keep the
        // last good frame counts on screen meanwhile.
      }
    }, refreshSeconds * 1000);
    return () => window.clearInterval(interval);
  }, [job, refreshSeconds]);

  async function refreshNow(current: Job) {
    const fresh = await getJob(current.id);
    if (fresh) setJob(fresh);
  }

  async function handlePauseToggle() {
    if (!job) return;
    if (job.isPaused) await unpauseJobs([job]);
    else await pauseJobs([job]);
    await refreshNow(job);
  }

  async function handleKill() {
    if (!job) return;
    if (!window.confirm(`Are you sure you want to kill this job?\n${job.name}`)) return;
    await killJobs([job], username, `Manual Job Kill Request in CueProgBar by ${username}`);
    await refreshNow(job);
  }

  async function handleRetryDead() {
    if (!job) return;
    const dead = job.jobStats.deadFrames;
    if (dead <= 0) return;
    if (!window.confirm(`Are you sure you want to retry ${dead} dead frame(s)?\n${job.name}`)) return;
    await retryJobsDeadFrames([job]);
    await refreshNow(job);
  }

  return (
    <div className="space-y-6">
      <form
        className="flex items-end gap-2"
        onSubmit={(event) => {
          event.preventDefault();
          void loadJob(nameInput);
        }}
      >
        <div className="flex-1">
          <Label htmlFor="cpb-job-name">Job name</Label>
          <Input
            id="cpb-job-name"
            className="mt-1"
            placeholder="show-shot-user_jobname"
            value={nameInput}
            onChange={(event) => setNameInput(event.target.value)}
          />
        </div>
        <Button type="submit" disabled={loading || !nameInput.trim()}>
          {loading ? "Loading…" : "Load"}
        </Button>
        <Button type="button" variant="outline" onClick={() => openPluginSettings(manifest.name)}>
          Settings
        </Button>
      </form>

      {error && (
        <p className="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          {error}
        </p>
      )}

      {job ? (
        <JobProgress
          job={job}
          username={username}
          onPauseToggle={handlePauseToggle}
          onKill={handleKill}
          onRetryDead={handleRetryDead}
        />
      ) : (
        !error && (
          <p className="text-sm text-muted-foreground">
            Enter a job name and select <span className="font-medium">Load</span> to monitor it.
            Polls every {refreshSeconds}s. This is a CueWeb port of CueGUI&apos;s{" "}
            <code className="rounded bg-muted px-1 py-0.5 font-mono text-xs">{manifest.name}</code>{" "}
            sample.
          </p>
        )
      )}
    </div>
  );
}

/** The progress bar, status labels, and job controls for a resolved job. */
function JobProgress({
  job,
  username,
  onPauseToggle,
  onKill,
  onRetryDead,
}: {
  job: Job;
  username: string;
  onPauseToggle: () => void;
  onKill: () => void;
  onRetryDead: () => void;
}) {
  const stats = job.jobStats;
  const total = stats.totalFrames;
  const done = stats.succeededFrames + stats.eatenFrames;
  const running = stats.runningFrames;
  const dead = stats.deadFrames;
  const finished = job.state === "FINISHED";

  // Status badge, identical logic to cueprogbar's paintEvent.
  let status: string;
  if (finished) status = "DONE";
  else if (dead > 0 || total === 0) status = "ERR";
  else status = `${Math.floor((done / total) * 100)}%`;

  const segments = FRAME_STATES.map((state) => ({
    ...state,
    count: stats[state.key],
    pct: total > 0 ? (stats[state.key] / total) * 100 : 0,
  }));

  return (
    <div className="rounded-lg border bg-card p-4 text-card-foreground shadow-sm">
      <div className="mb-2 flex items-center justify-between gap-3">
        <span className="truncate font-mono text-sm" title={job.name}>
          {job.name}
        </span>
        <span
          className={cn(
            "shrink-0 rounded px-1.5 py-0.5 text-xs font-semibold",
            finished
              ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300"
              : status === "ERR"
                ? "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300"
                : "bg-muted text-foreground",
          )}
        >
          {status}
        </span>
      </div>

      {/* Color-coded bar, one block per non-zero frame state. */}
      <div
        className="flex h-4 w-full overflow-hidden rounded border bg-muted"
        role="img"
        aria-label={`${done} of ${total} frames done, ${running} running, ${dead} dead`}
      >
        {segments
          .filter((segment) => segment.count > 0)
          .map((segment) => (
            <div
              key={segment.key}
              style={{ width: `${segment.pct}%`, backgroundColor: segment.color }}
              title={`${segment.count} ${segment.label}`}
            />
          ))}
      </div>

      <p className="mt-2 text-sm text-muted-foreground">
        {done} of {total} done, {running} running{job.isPaused && !finished ? " · Paused" : ""}
      </p>

      {/* Legend with per-state counts — parity with cueprogbar's left-click menu. */}
      <ul className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs">
        {segments
          .filter((segment) => segment.count > 0)
          .map((segment) => (
            <li key={segment.key} className="flex items-center gap-1.5">
              <span
                className="inline-block h-3 w-3 rounded-sm border"
                style={{ backgroundColor: segment.color }}
              />
              <span className="font-mono">{segment.count}</span>
              <span className="text-muted-foreground">{segment.label}</span>
            </li>
          ))}
      </ul>

      {/* Job controls — parity with cueprogbar's right-click menu. */}
      {!finished && (
        <div className="mt-4 flex flex-wrap gap-2">
          <Button type="button" variant="outline" size="sm" onClick={onPauseToggle}>
            {job.isPaused ? "Unpause Job" : "Pause Job"}
          </Button>
          {dead > 0 && (
            <Button type="button" variant="outline" size="sm" onClick={onRetryDead}>
              Retry Dead Frames
            </Button>
          )}
          <Button type="button" variant="destructive" size="sm" onClick={onKill}>
            Kill Job
          </Button>
        </div>
      )}
    </div>
  );
}
