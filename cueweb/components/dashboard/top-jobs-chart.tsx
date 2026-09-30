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
import { Flame } from "lucide-react";
import type { ActiveElement, ChartEvent, TooltipItem } from "chart.js";
import { useRouter } from "next/navigation";
import * as React from "react";
import { Bar } from "react-chartjs-2";

ensureChartJsRegistered();

const REFRESH_MS = 15000;
const TOP_N = 10;
// Trim long job names in the y-axis tick labels so the chart stays readable
// without truncating the tooltip (which always shows the full name).
const MAX_TICK_CHARS = 32;

function truncate(name: string): string {
  if (name.length <= MAX_TICK_CHARS) return name;
  return `${name.slice(0, MAX_TICK_CHARS - 1)}…`;
}

export function TopJobsChart() {
  const [jobs, setJobs] = React.useState<Job[] | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const colors = useChartColors();
  const router = useRouter();

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

  const top = React.useMemo(() => {
    return [...(jobs ?? [])]
      .filter((j) => (j.jobStats?.runningFrames ?? 0) > 0)
      .sort(
        (a, b) =>
          (b.jobStats?.runningFrames ?? 0) - (a.jobStats?.runningFrames ?? 0),
      )
      .slice(0, TOP_N);
  }, [jobs]);

  const data = {
    labels: top.map((j) => truncate(j.name)),
    datasets: [
      {
        label: "Running frames",
        data: top.map((j) => j.jobStats?.runningFrames ?? 0),
        backgroundColor: colors.series[0],
        borderRadius: 3,
        maxBarThickness: 18,
      },
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    indexAxis: "y" as const,
    onHover: (event: ChartEvent, elements: ActiveElement[]) => {
      const target = event.native?.target as HTMLElement | undefined;
      if (target) target.style.cursor = elements.length ? "pointer" : "default";
    },
    onClick: (_event: ChartEvent, elements: ActiveElement[]) => {
      if (elements.length === 0) return;
      const idx = elements[0].index;
      const job = top[idx];
      if (!job) return;
      router.push(
        `/jobs/${encodeURIComponent(job.name)}?jobId=${encodeURIComponent(job.id)}`,
      );
    },
    plugins: {
      legend: { display: false },
      tooltip: {
        callbacks: {
          // Use the un-truncated job name in the tooltip header.
          title: (items: TooltipItem<"bar">[]) =>
            top[items[0]?.dataIndex]?.name ?? "",
          label: (ctx: TooltipItem<"bar">) => {
            const v = (ctx.parsed.x ?? 0) as number;
            return `${v.toLocaleString()} running frames`;
          },
        },
      },
    },
    scales: {
      x: {
        beginAtZero: true,
        ticks: { color: colors.mutedText, precision: 0 },
        grid: { color: colors.grid },
      },
      y: {
        ticks: { color: colors.text, font: { size: 11 } },
        grid: { display: false },
      },
    },
  };

  return (
    <ChartCard
      title="Top Jobs by Running Frames"
      subtitle={top.length > 0 ? `Top ${top.length} active jobs` : "No running jobs"}
      icon={<Flame className="h-4 w-4" />}
      loading={jobs === null && !error}
      error={jobs === null && error ? "Could not load jobs from Cuebot." : null}
      footer="Click a bar to open that job's detail page."
    >
      {top.length === 0 ? (
        <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
          No jobs have running frames right now.
        </div>
      ) : (
        <Bar data={data} options={options} />
      )}
    </ChartCard>
  );
}
