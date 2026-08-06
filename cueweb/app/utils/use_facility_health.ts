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

/**
 * Polls /api/facility/health every 30s and returns a per-facility status map
 * keyed by facility name. Used by the Cuebot Facility menu to render a green/red
 * dot per facility and to block selecting a facility whose gateway is down (J2).
 *
 * `undefined` for a facility means "not yet probed" (render neutral). Polls are
 * serialized with an AbortController so a slow probe can't stomp fresher state.
 */

export interface FacilityHealth {
  ok: boolean;
  latencyMs: number;
  error?: string;
}

const POLL_INTERVAL_MS = 30_000;

export function useFacilityHealth(): {
  health: Record<string, FacilityHealth>;
  loading: boolean;
} {
  const [health, setHealth] = React.useState<Record<string, FacilityHealth>>({});
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    let cancelled = false;
    let inFlight: AbortController | null = null;

    async function check() {
      inFlight?.abort();
      const controller = new AbortController();
      inFlight = controller;
      try {
        const res = await fetch("/api/facility/health", {
          cache: "no-store",
          signal: controller.signal,
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const body = (await res.json()) as {
          facilities?: Array<{ name: string; ok: boolean; latencyMs: number; error?: string }>;
        };
        if (cancelled || inFlight !== controller) return;
        const map: Record<string, FacilityHealth> = {};
        for (const f of body.facilities ?? []) {
          map[f.name] = { ok: f.ok, latencyMs: f.latencyMs, error: f.error };
        }
        setHealth(map);
      } catch (err) {
        if ((err as { name?: string })?.name === "AbortError") return;
        // Leave the last-known map in place on a transient failure.
      } finally {
        if (!cancelled && inFlight === controller) setLoading(false);
      }
    }

    void check();
    const id = setInterval(check, POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      inFlight?.abort();
      clearInterval(id);
    };
  }, []);

  return { health, loading };
}
