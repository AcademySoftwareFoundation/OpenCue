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

import { usePathname } from "next/navigation";
import * as React from "react";
import { Activity, Clock, Tag } from "lucide-react";

import { cn } from "@/lib/utils";

/**
 * IDE-style fixed status bar mounted at the bottom of every authenticated
 * route. Renders three metrics, each with a tooltip:
 *
 *   1. REST gateway status (Online / Offline + ping latency).
 *      Polled via `/api/health` every 10s. The bar surface turns red
 *      when the gateway is offline.
 *   2. Last successful jobs-table refresh. Updated when the jobs data
 *      table dispatches a `cueweb:jobs-refreshed` CustomEvent.
 *   3. CueWeb build version (NEXT_PUBLIC_APP_VERSION, falls back to the
 *      package.json version baked in by next.config.js).
 *
 * Hidden on `/login*`.
 */

interface HealthBody {
  gatewayOnline: boolean;
  status: number;
  latencyMs: number;
  checkedAt: string;
  error?: string;
}

const POLL_INTERVAL_MS = 10_000;

function formatRelative(iso: string | null): string {
  if (!iso) return "—";
  const ts = new Date(iso).getTime();
  if (Number.isNaN(ts)) return "—";
  const diff = Math.max(0, Date.now() - ts);
  const sec = Math.floor(diff / 1000);
  if (sec < 5) return "just now";
  if (sec < 60) return `${sec}s ago`;
  const min = Math.floor(sec / 60);
  if (min < 60) return `${min}m ago`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr}h ago`;
  const day = Math.floor(hr / 24);
  return `${day}d ago`;
}

function StatusItem({
  icon: Icon,
  label,
  title,
  tone = "default",
}: {
  icon: typeof Activity;
  label: React.ReactNode;
  title: string;
  tone?: "default" | "ok" | "warn" | "error";
}) {
  return (
    <div
      title={title}
      className={cn(
        "flex items-center gap-1.5 px-2 py-0.5 text-[11px]",
        tone === "ok" && "text-emerald-700 dark:text-emerald-300",
        tone === "warn" && "text-amber-700 dark:text-amber-300",
        tone === "error" && "text-red-700 dark:text-red-300",
      )}
    >
      <Icon className="h-3 w-3 shrink-0" aria-hidden="true" />
      <span className="truncate">{label}</span>
    </div>
  );
}

export function StatusBar() {
  const pathname = usePathname();
  const [health, setHealth] = React.useState<HealthBody | null>(null);
  const [lastRefresh, setLastRefresh] = React.useState<string | null>(null);
  // Tick once per second so relative timestamps stay fresh without waiting
  // for the next poll.
  const [, setTick] = React.useState<number>(0);

  React.useEffect(() => {
    if (pathname?.startsWith("/login")) return;

    let cancelled = false;
    // Serialize health polls with an AbortController so a slow probe can't
    // arrive out-of-order and stomp on fresher state. Each tick aborts any
    // still-running previous fetch and only publishes state when its own
    // controller is still the active one.
    let inFlight: AbortController | null = null;

    async function check() {
      inFlight?.abort();
      const controller = new AbortController();
      inFlight = controller;
      try {
        const res = await fetch("/api/health", {
          cache: "no-store",
          signal: controller.signal,
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const body = (await res.json()) as HealthBody;
        if (!cancelled && inFlight === controller) setHealth(body);
      } catch (err) {
        // Ignore aborts triggered by the next tick / unmount; only the
        // freshest poll should publish state.
        if ((err as { name?: string })?.name === "AbortError") return;
        if (!cancelled && inFlight === controller) {
          setHealth({
            gatewayOnline: false,
            status: 0,
            latencyMs: 0,
            checkedAt: new Date().toISOString(),
            error: String(err),
          });
        }
      }
    }

    void check();
    const id = setInterval(check, POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      inFlight?.abort();
      clearInterval(id);
    };
  }, [pathname]);

  // Subscribe to the jobs table's last-refresh event.
  React.useEffect(() => {
    const handler = (event: Event) => {
      const detail = (event as CustomEvent<{ at?: string }>).detail;
      if (detail?.at) setLastRefresh(detail.at);
    };
    window.addEventListener("cueweb:jobs-refreshed", handler);
    return () => window.removeEventListener("cueweb:jobs-refreshed", handler);
  }, []);

  // Keep the relative timestamps ticking once per second.
  React.useEffect(() => {
    const id = setInterval(() => setTick((n) => n + 1), 1000);
    return () => clearInterval(id);
  }, []);

  if (pathname?.startsWith("/login")) return null;

  const version =
    process.env.NEXT_PUBLIC_APP_VERSION && process.env.NEXT_PUBLIC_APP_VERSION.length > 0
      ? process.env.NEXT_PUBLIC_APP_VERSION
      : "dev";

  const gatewayOnline = health?.gatewayOnline ?? false;
  // While we haven't received the first probe yet, treat the bar as neutral
  // (not red) so a slow first poll doesn't briefly flash an error state.
  const showAsError = health !== null && !gatewayOnline;

  const gatewayTitle = health
    ? gatewayOnline
      ? `REST gateway reachable (HTTP ${health.status}, ${health.latencyMs}ms round-trip, checked ${formatRelative(health.checkedAt)})`
      : `REST gateway unreachable${health.error ? `: ${health.error}` : ""} (checked ${formatRelative(health.checkedAt)})`
    : "REST gateway status check in progress…";

  const refreshTitle = lastRefresh
    ? `Jobs table last refreshed at ${new Date(lastRefresh).toLocaleTimeString()}`
    : "Jobs table has not refreshed yet in this session";

  return (
    <footer
      role="contentinfo"
      aria-label="CueWeb status bar"
      className={cn(
        "fixed inset-x-0 bottom-0 z-30 flex h-6 items-center gap-1 border-t border-border bg-background/95 px-3 text-[11px] backdrop-blur",
        "dark:border-zinc-800 dark:bg-zinc-900/95",
        showAsError &&
          "border-red-500/50 bg-red-100 dark:border-red-700/50 dark:bg-red-950/40",
      )}
    >
      <StatusItem
        icon={Activity}
        tone={health === null ? "default" : gatewayOnline ? "ok" : "error"}
        title={gatewayTitle}
        label={
          <span className="inline-flex items-center gap-1.5">
            <span
              aria-hidden="true"
              className={cn(
                "inline-block h-1.5 w-1.5 rounded-full",
                health === null
                  ? "bg-muted-foreground"
                  : gatewayOnline
                    ? "bg-emerald-500"
                    : "bg-red-500",
              )}
            />
            Gateway: {health === null ? "checking…" : gatewayOnline ? "Online" : "Offline"}
            {health && gatewayOnline && (
              <span className="text-muted-foreground"> ({health.latencyMs}ms)</span>
            )}
          </span>
        }
      />

      <span className="mx-1 h-3 w-px bg-border dark:bg-zinc-700" aria-hidden="true" />

      <StatusItem
        icon={Clock}
        title={refreshTitle}
        label={<>Last refresh: {formatRelative(lastRefresh)}</>}
      />

      <span className="ml-auto" />

      <StatusItem
        icon={Tag}
        title={`CueWeb build version ${version}`}
        label={<>v{version}</>}
      />
    </footer>
  );
}
