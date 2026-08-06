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

import { Host, getHosts } from "@/app/utils/get_utils";
import {
  ChartCard,
  useChartColors,
} from "@/components/dashboard/chart-card";
import { ensureChartJsRegistered } from "@/components/dashboard/chart-register";
import { Server } from "lucide-react";
import * as React from "react";
import { Doughnut } from "react-chartjs-2";

ensureChartJsRegistered();

const REFRESH_MS = 60000;

// Mirrors hardware.HardwareState in proto/src/host.proto. Order matters for
// chart legend stability across refreshes.
const STATE_ORDER = ["UP", "DOWN", "REBOOTING", "REPAIR"] as const;
type StateKey = (typeof STATE_ORDER)[number];

const STATE_COLORS: Record<StateKey, string> = {
  UP: "#10b981",        // emerald-500
  DOWN: "#ef4444",      // red-500
  REBOOTING: "#f59e0b", // amber-500
  REPAIR: "#a855f7",    // purple-500
};

const STATE_LABELS: Record<StateKey, string> = {
  UP: "Up",
  DOWN: "Down",
  REBOOTING: "Rebooting",
  REPAIR: "Repair",
};

export function HostsStateChart() {
  const [hosts, setHosts] = React.useState<Host[] | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const colors = useChartColors();

  React.useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const data = await getHosts();
        if (!cancelled) {
          setHosts(data);
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
    const out: Record<StateKey, number> = {
      UP: 0,
      DOWN: 0,
      REBOOTING: 0,
      REPAIR: 0,
    };
    for (const host of hosts ?? []) {
      const state = host.state as StateKey;
      if (state in out) out[state] += 1;
    }
    return out;
  }, [hosts]);

  const total = STATE_ORDER.reduce((acc, s) => acc + counts[s], 0);
  const locked = (hosts ?? []).filter(
    (h) => h.lockState && h.lockState !== "OPEN",
  ).length;

  const data = {
    labels: STATE_ORDER.map((s) => STATE_LABELS[s]),
    datasets: [
      {
        data: STATE_ORDER.map((s) => counts[s]),
        backgroundColor: STATE_ORDER.map((s) => STATE_COLORS[s]),
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
            const pct = total > 0 ? ((ctx.parsed / total) * 100).toFixed(1) : "0.0";
            return `${ctx.label}: ${ctx.parsed.toLocaleString()} (${pct}%)`;
          },
        },
      },
    },
  };

  return (
    <ChartCard
      title="Hosts by State"
      subtitle={
        total > 0
          ? `${total} hosts - ${locked} locked (NLE / DISABLED)`
          : "No hosts reporting"
      }
      icon={<Server className="h-4 w-4" />}
      loading={hosts === null && !error}
      error={hosts === null && error ? "Could not load hosts from Cuebot." : null}
    >
      {total === 0 ? (
        <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
          No hosts have reported yet.
        </div>
      ) : (
        <Doughnut data={data} options={options} />
      )}
    </ChartCard>
  );
}
