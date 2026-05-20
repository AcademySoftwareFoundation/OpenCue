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

import { createJwtToken } from "@/app/utils/api_utils";

interface JwtParams {
  sub: string;
  role: string;
  iat: number;
  exp: number;
}

/**
 * Cheap REST gateway reachability check used by the bottom status bar.
 * Issues a JWT-signed POST against ShowInterface/GetActiveShows (a small
 * read-only call that returns quickly) and measures latency. The response
 * shape is intentionally compact so the status bar can poll it every 10s
 * without producing visible noise in the network panel.
 *
 * Note: this endpoint does not surface gateway response payloads; it only
 * reports whether the gateway answered and how long the round-trip took.
 */

interface HealthBody {
  gatewayOnline: boolean;
  /** Gateway HTTP status (when reachable); 0 if the request never returned. */
  status: number;
  /** Round-trip time in milliseconds (server -> gateway -> server). */
  latencyMs: number;
  /** ISO-8601 timestamp of when the health probe ran. */
  checkedAt: string;
  /** Optional human-readable hint when offline. */
  error?: string;
}

export async function GET(): Promise<NextResponse<HealthBody>> {
  const gateway = process.env.NEXT_PUBLIC_OPENCUE_ENDPOINT;
  const checkedAt = new Date().toISOString();

  if (!gateway) {
    return NextResponse.json(
      {
        gatewayOnline: false,
        status: 0,
        latencyMs: 0,
        checkedAt,
        error: "NEXT_PUBLIC_OPENCUE_ENDPOINT is not configured",
      },
      { status: 200 },
    );
  }

  const jwtParams: JwtParams = {
    sub: "cueweb-status-bar",
    role: "user-role",
    iat: Math.floor(Date.now() / 1000),
    exp: Math.floor(Date.now() / 1000) + 60,
  };

  let token: string;
  try {
    token = createJwtToken(jwtParams);
  } catch (err) {
    return NextResponse.json(
      {
        gatewayOnline: false,
        status: 0,
        latencyMs: 0,
        checkedAt,
        error: `JWT signing failed: ${String(err)}`,
      },
      { status: 200 },
    );
  }

  const start = Date.now();
  let status = 0;
  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 5000);

    const response = await fetch(`${gateway}/show.ShowInterface/GetActiveShows`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: "{}",
      cache: "no-store",
      signal: controller.signal,
    });
    clearTimeout(timer);
    status = response.status;
    // Drain the body so the connection can be reused / closed cleanly.
    await response.text().catch(() => undefined);

    const latencyMs = Date.now() - start;
    return NextResponse.json(
      {
        gatewayOnline: response.ok,
        status,
        latencyMs,
        checkedAt,
      },
      { status: 200 },
    );
  } catch (err) {
    return NextResponse.json(
      {
        gatewayOnline: false,
        status,
        latencyMs: Date.now() - start,
        checkedAt,
        error: String(err),
      },
      { status: 200 },
    );
  }
}
