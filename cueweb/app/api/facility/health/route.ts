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

import { NextResponse } from "next/server";

import { createJwtToken } from "@/app/utils/gateway_server";
import { getAllFacilityTargets } from "@/lib/facility-server";

/**
 * Per-facility connection health (J2). Probes every configured facility's REST
 * gateway in parallel and returns `{ name, ok, latencyMs }[]`, so the header
 * facility menu can show a green/red dot per facility and disable selecting a
 * facility whose gateway is down. Probes use a short timeout and never surface
 * gateway payloads — only reachability + round-trip time.
 */

const PROBE_TIMEOUT_MS = 5000;

interface FacilityHealth {
  name: string;
  ok: boolean;
  latencyMs: number;
  error?: string;
}

async function probe(name: string, gatewayUrl: string, jwtSecret: string): Promise<FacilityHealth> {
  if (!gatewayUrl) {
    return { name, ok: false, latencyMs: 0, error: "No gateway configured" };
  }

  let token: string;
  try {
    token = createJwtToken(
      {
        sub: "cueweb-facility-health",
        role: "user-role",
        iat: Math.floor(Date.now() / 1000),
        exp: Math.floor(Date.now() / 1000) + 60,
      },
      jwtSecret,
    );
  } catch {
    return { name, ok: false, latencyMs: 0, error: "JWT signing failed" };
  }

  const start = Date.now();
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), PROBE_TIMEOUT_MS);
  try {
    const response = await fetch(`${gatewayUrl}/show.ShowInterface/GetActiveShows`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      body: "{}",
      cache: "no-store",
      signal: controller.signal,
    });
    await response.text().catch(() => undefined);
    return { name, ok: response.ok, latencyMs: Date.now() - start };
  } catch {
    return { name, ok: false, latencyMs: Date.now() - start, error: "Gateway probe failed" };
  } finally {
    clearTimeout(timer);
  }
}

export async function GET(): Promise<NextResponse> {
  const targets = await getAllFacilityTargets();
  const facilities = await Promise.all(
    targets.map((t) => probe(t.name, t.gatewayUrl, t.jwtSecret)),
  );
  return NextResponse.json(
    { facilities, checkedAt: new Date().toISOString() },
    { status: 200 },
  );
}
