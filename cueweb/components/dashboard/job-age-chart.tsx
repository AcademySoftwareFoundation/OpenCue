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
  useChartColors,
} from "@/components/dashboard/chart-card";
import { ensureChartJsRegistered } from "@/components/dashboard/chart-register";
import type { TooltipItem } from "chart.js";
import { Clock } from "lucide-react";
import * as React from "react";
import { Bar } from "react-chartjs-2";

ensureChartJsRegistered();

const REFRESH_MS = 30000;

interface Bucket {
  label: string;
  /** Inclusive lower bound in seconds. */
  minSec: number;
  /** Exclusive upper bound in seconds. Use Infinity for the open-ended bucket. */
  maxSec: number;
  /** Visual cue: fresher = green, older = red. */
  color: string;
}

const HOUR = 3600;
const DAY = 24 * HOUR;

const BUCKETS: Bucket[] = [
  { label: "< 1h", minSec: 0, maxSec: HOUR, color: "#10b981" },
  { label: "1-6h", minSec: HOUR, maxSec: 6 * HOUR, color: "#22c55e" },
  { label: "6-24h", minSec: 6 * HOUR, maxSec: DAY, color: "#f59e0b" },
  { label: "1-3d", minSec: DAY, maxSec: 3 * DAY, color: "#f97316" },
  { label: "> 3d", minSec: 3 * DAY, maxSec: Number.POSITIVE_INFINITY, color: "#ef4444" },
];

export function JobAgeChart() {
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

  const counts = React.useMemo(() => {
    const out = BUCKETS.map(() => 0);
    if (!jobs || jobs.length === 0) return out;
    const now = Math.floor(Date.now() / 1000);
    for (const job of jobs) {
      if (!job.startTime) continue;
      // Active jobs only (we already filter via include_finished:false). Use
      // current time even if stopTime is set - finished jobs that linger in
      // the list still age out into the same buckets.
      const age = Math.max(0, now - job.startTime);
      const idx = BUCKETS.findIndex(
        (b) => age >= b.minSec && age < b.maxSec,
      );
      if (idx >= 0) out[idx] += 1;
    }
    return out;
  }, [jobs]);

  const total = counts.reduce((a, b) => a + b, 0);

  const data = {
    labels: BUCKETS.map((b) => b.label),
    datasets: [
      {
        label: "Active jobs",
        data: counts,
        backgroundColor: BUCKETS.map((b) => b.color),
        borderRadius: 3,
        maxBarThickness: 36,
      },
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        callbacks: {
          label: (ctx: TooltipItem<"bar">) => {
            const v = (ctx.parsed.y ?? 0) as number;
            return `${v.toLocaleString()} job${v === 1 ? "" : "s"}`;
          },
        },
      },
    },
    scales: {
      x: {
        ticks: { color: colors.text, font: { size: 11 } },
        grid: { display: false },
      },
      y: {
        beginAtZero: true,
        ticks: { color: colors.mutedText, precision: 0 },
        grid: { color: colors.grid },
      },
    },
  };

  return (
    <ChartCard
      title="Job Age Distribution"
      subtitle={
        total > 0
          ? `${total} active jobs - greener = fresher`
          : "No active jobs"
      }
      icon={<Clock className="h-4 w-4" />}
      loading={jobs === null && !error}
      error={jobs === null && error ? "Could not load jobs from Cuebot." : null}
      footer="Stuck jobs cluster in the right-most red bars."
    >
      {total === 0 ? (
        <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
          No active jobs to chart.
        </div>
      ) : (
        <Bar data={data} options={options} />
      )}
    </ChartCard>
  );
}
