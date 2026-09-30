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
  ChartCard,
  FRAME_STATE_COLORS,
  useChartColors,
} from "@/components/dashboard/chart-card";
import { ensureChartJsRegistered } from "@/components/dashboard/chart-register";
import { PieChart } from "lucide-react";
import * as React from "react";
import { Doughnut } from "react-chartjs-2";

ensureChartJsRegistered();

const REFRESH_MS = 30000;

const STATE_ORDER = [
  "Running",
  "Waiting",
  "Succeeded",
  "Dead",
  "Eaten",
  "Depend",
  "Pending",
] as const;

type StateKey = (typeof STATE_ORDER)[number];

const STATE_TO_FIELD: Record<StateKey, keyof Job["jobStats"]> = {
  Running: "runningFrames",
  Waiting: "waitingFrames",
  Succeeded: "succeededFrames",
  Dead: "deadFrames",
  Eaten: "eatenFrames",
  Depend: "dependFrames",
  Pending: "pendingFrames",
};

export function FrameStateChart() {
  const [jobs, setJobs] = React.useState<Job[] | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const colors = useChartColors();

  React.useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const body = JSON.stringify({ r: { include_finished: false } });
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

  const totals = React.useMemo(() => {
    const out: Record<StateKey, number> = {
      Running: 0,
      Waiting: 0,
      Succeeded: 0,
      Dead: 0,
      Eaten: 0,
      Depend: 0,
      Pending: 0,
    };
    for (const job of jobs ?? []) {
      const stats = job.jobStats;
      if (!stats) continue;
      for (const state of STATE_ORDER) {
        const field = STATE_TO_FIELD[state];
        const value = stats[field];
        if (typeof value === "number") out[state] += value;
      }
    }
    return out;
  }, [jobs]);

  const totalFrames = STATE_ORDER.reduce((acc, s) => acc + totals[s], 0);

  const data = {
    labels: STATE_ORDER as unknown as string[],
    datasets: [
      {
        data: STATE_ORDER.map((s) => totals[s]),
        backgroundColor: STATE_ORDER.map((s) => FRAME_STATE_COLORS[s]),
        borderColor: "transparent",
        borderWidth: 0,
        hoverOffset: 6,
      },
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    cutout: "60%",
    plugins: {
      legend: {
        position: "right" as const,
        labels: {
          color: colors.text,
          font: { size: 11 },
          boxWidth: 10,
          boxHeight: 10,
          padding: 8,
        },
      },
      tooltip: {
        callbacks: {
          label: (ctx: { label?: string; parsed: number }) => {
            const pct = totalFrames > 0 ? ((ctx.parsed / totalFrames) * 100).toFixed(1) : "0.0";
            return `${ctx.label}: ${ctx.parsed.toLocaleString()} (${pct}%)`;
          },
        },
      },
    },
  };

  return (
    <ChartCard
      title="Frame State Breakdown"
      subtitle={
        jobs && jobs.length > 0
          ? `${totalFrames.toLocaleString()} frames across ${jobs.length} active jobs`
          : "All active jobs"
      }
      icon={<PieChart className="h-4 w-4" />}
      loading={jobs === null && !error}
      error={jobs === null && error ? "Could not load jobs from Cuebot." : null}
    >
      {totalFrames === 0 ? (
        <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
          No frames reported by any active job.
        </div>
      ) : (
        <Doughnut data={data} options={options} />
      )}
    </ChartCard>
  );
}
