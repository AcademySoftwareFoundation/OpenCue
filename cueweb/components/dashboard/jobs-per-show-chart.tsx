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
import { Film } from "lucide-react";
import * as React from "react";
import { Bar } from "react-chartjs-2";

ensureChartJsRegistered();

const REFRESH_MS = 30000;
const TOP_N = 8;
const OTHER_LABEL = "Other";

export function JobsPerShowChart() {
  const [jobs, setJobs] = React.useState<Job[] | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const colors = useChartColors();
  // Guards against the setInterval ticking again while a previous fetch
  // is still pending. Without it a slow Cuebot can stack overlapping
  // requests every REFRESH_MS, wasting bandwidth and causing
  // stale-response races (a late tick can overwrite a newer one).
  const inFlight = React.useRef(false);

  React.useEffect(() => {
    let cancelled = false;
    const load = async () => {
      if (inFlight.current) return;
      inFlight.current = true;
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
      } finally {
        inFlight.current = false;
      }
    };
    load();
    const interval = setInterval(load, REFRESH_MS);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  const buckets = React.useMemo(() => {
    const tally = new Map<string, number>();
    for (const job of jobs ?? []) {
      const show = job.show?.trim() || "(none)";
      tally.set(show, (tally.get(show) ?? 0) + 1);
    }
    const sorted = Array.from(tally.entries()).sort((a, b) => b[1] - a[1]);
    const top = sorted.slice(0, TOP_N);
    const rest = sorted.slice(TOP_N);
    const otherCount = rest.reduce((acc, [, n]) => acc + n, 0);
    if (otherCount > 0) top.push([OTHER_LABEL, otherCount]);
    return top;
  }, [jobs]);

  const data = {
    labels: buckets.map(([show]) => show),
    datasets: [
      {
        label: "Active jobs",
        data: buckets.map(([, n]) => n),
        backgroundColor: buckets.map(
          (_, i) => colors.series[i % colors.series.length],
        ),
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
        ticks: { color: colors.text, font: { size: 11 }, maxRotation: 30 },
        grid: { display: false },
      },
      y: {
        beginAtZero: true,
        ticks: { color: colors.mutedText, precision: 0 },
        grid: { color: colors.grid },
      },
    },
  };

  const total = buckets.reduce((acc, [, n]) => acc + n, 0);

  return (
    <ChartCard
      title="Jobs per Show"
      subtitle={
        total > 0
          ? `${total} active jobs across ${buckets.length} show${buckets.length === 1 ? "" : "s"}`
          : "No active jobs"
      }
      icon={<Film className="h-4 w-4" />}
      loading={jobs === null && !error}
      error={jobs === null && error ? "Could not load jobs from Cuebot." : null}
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
