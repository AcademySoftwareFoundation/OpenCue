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
import { useSession } from "next-auth/react";

import type { Frame } from "@/app/frames/frame-columns";
import { StuckFrame, getStuckFrames } from "@/app/utils/get_utils";
import { killFrames, retryFrames } from "@/app/utils/action_utils";
import { handleError } from "@/app/utils/notify_utils";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

const REFRESH_MS = 30000;
const THRESHOLD_KEY = "cueweb.stuck-frames.thresholdHours";
const DEFAULT_HOURS = 8;
const MIN_HOURS = 1;
const MAX_HOURS = 48;

function fmtDuration(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds < 0) return "—";
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  return `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

// last_resource is "host/procid"; show just the host.
const hostOf = (lastResource: string) => (lastResource || "").split("/")[0] || "—";

export default function StuckFramesPage() {
  const { data: session } = useSession();
  const username = session?.user?.name ?? session?.user?.email ?? "cueweb";

  const [frames, setFrames] = React.useState<StuckFrame[] | null>(null);
  const [thresholdHours, setThresholdHours] = React.useState(DEFAULT_HOURS);
  const [now, setNow] = React.useState(() => Date.now() / 1000);
  const [busyId, setBusyId] = React.useState<string | null>(null);

  const load = React.useCallback(async (isCancelled?: () => boolean) => {
    try {
      const data = await getStuckFrames();
      if (isCancelled?.()) return;
      setFrames(data);
      setNow(Date.now() / 1000);
    } catch (err) {
      if (isCancelled?.()) return;
      handleError(err, "Could not load stuck frames");
      setFrames((prev) => prev ?? []);
    }
  }, []);

  React.useEffect(() => {
    // Restore the persisted threshold on mount (kept out of the initial state
    // to avoid an SSR/client hydration mismatch).
    const stored = window.localStorage.getItem(THRESHOLD_KEY);
    if (stored) {
      const n = Number(stored);
      if (Number.isFinite(n) && n >= MIN_HOURS && n <= MAX_HOURS) setThresholdHours(n);
    }
    let cancelled = false;
    const isCancelled = () => cancelled;
    load(isCancelled);
    const interval = setInterval(() => load(isCancelled), REFRESH_MS);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [load]);

  function changeThreshold(hours: number) {
    setThresholdHours(hours);
    window.localStorage.setItem(THRESHOLD_KEY, String(hours));
  }

  const runtimeOf = React.useCallback(
    (f: StuckFrame) => (f.startTime ? now - f.startTime : 0),
    [now],
  );

  const stuck = React.useMemo(() => {
    if (!frames) return null;
    const thresholdSeconds = thresholdHours * 3600;
    return frames
      .filter((f) => runtimeOf(f) > thresholdSeconds)
      .sort((a, b) => runtimeOf(b) - runtimeOf(a));
  }, [frames, thresholdHours, runtimeOf]);

  // Strip the page-only jobId/jobName before sending the frame to a Cuebot RPC
  // (they are not Frame proto fields).
  function toFrame(sf: StuckFrame): Frame {
    const { jobId: _jobId, jobName: _jobName, ...frame } = sf;
    return frame as Frame;
  }

  async function handleRetry(sf: StuckFrame) {
    setBusyId(sf.id);
    try {
      await retryFrames([toFrame(sf)]);
      await load();
    } finally {
      setBusyId(null);
    }
  }

  async function handleKill(sf: StuckFrame) {
    setBusyId(sf.id);
    try {
      await killFrames([toFrame(sf)], username, `Manual frame kill from CueWeb Stuck Frames by ${username}`);
      await load();
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="p-4">
      <h1 className="mb-4 text-lg font-semibold">Stuck Frames</h1>

      <div className="mb-4 flex flex-wrap items-center gap-4">
        <label className="flex items-center gap-3 text-sm">
          <span className="text-muted-foreground">Running longer than</span>
          <input
            type="range"
            min={MIN_HOURS}
            max={MAX_HOURS}
            step={1}
            value={thresholdHours}
            onChange={(e) => changeThreshold(Number(e.target.value))}
            className="h-2 w-64 cursor-pointer"
            aria-label="Threshold hours"
          />
          <span className="w-16 tabular-nums font-medium">
            {thresholdHours} {thresholdHours === 1 ? "hour" : "hours"}
          </span>
        </label>
        {stuck ? (
          <span className="text-sm text-muted-foreground">
            {stuck.length} {stuck.length === 1 ? "frame" : "frames"}
          </span>
        ) : null}
      </div>

      {stuck === null ? (
        <div className="space-y-2">
          <Skeleton className="h-8 w-full" />
          <Skeleton className="h-8 w-full" />
          <Skeleton className="h-8 w-full" />
        </div>
      ) : stuck.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          No frames have been running longer than {thresholdHours}{" "}
          {thresholdHours === 1 ? "hour" : "hours"}.
        </p>
      ) : (
        <div className="overflow-x-auto rounded-md border">
          <table className="w-full text-sm">
            <thead className="border-b bg-muted/40 text-left">
              <tr>
                <th className="p-2 font-medium">Job</th>
                <th className="p-2 font-medium">Layer</th>
                <th className="p-2 font-medium">Frame</th>
                <th className="p-2 font-medium">Host</th>
                <th className="p-2 font-medium">Runtime</th>
                <th className="p-2 text-right font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {stuck.map((f) => (
                <tr key={`${f.jobId}:${f.id}`} className="border-b last:border-0 hover:bg-muted/30">
                  <td className="max-w-[22rem] truncate p-2" title={f.jobName}>{f.jobName}</td>
                  <td className="p-2">{f.layerName}</td>
                  <td className="p-2 tabular-nums">{f.number}</td>
                  <td className="p-2">{hostOf(f.lastResource)}</td>
                  <td className="p-2 tabular-nums">{fmtDuration(runtimeOf(f))}</td>
                  <td className="p-2">
                    <div className="flex justify-end gap-2">
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        disabled={busyId === f.id}
                        onClick={() => handleRetry(f)}
                      >
                        Retry
                      </Button>
                      <Button
                        type="button"
                        variant="destructive"
                        size="sm"
                        disabled={busyId === f.id}
                        onClick={() => handleKill(f)}
                      >
                        Kill
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
