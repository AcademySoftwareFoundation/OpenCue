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

/**
 * SERVER-ONLY gateway helpers: sign JWTs and proxy requests to the OpenCue REST
 * gateway. Split out of `api_utils.ts` (which is part of the client bundle via
 * the `accessGetApi` / `accessActionApi` helpers) so this module can import the
 * filesystem-backed facility override store (`lib/facility-server.ts`) without
 * dragging `node:fs` into the client compilation.
 *
 * Only Route Handlers import from here.
 */

import jwt from "jsonwebtoken";
import { NextResponse } from "next/server";

import { handleError } from "./notify_utils";
import { getRequestFacilityTargetWithOverrides } from "@/lib/facility-server";
import { auditGatewayCall } from "@/lib/audit";
import MetricsService from "@/lib/metrics-service";

interface JwtParams {
  sub: string;
  role: string;
  iat: number;
  exp: number;
}

// Abort a gateway request that hasn't responded within this window so a stalled
// backend can't hold request threads. Generous enough for large list calls.
const GATEWAY_TIMEOUT_MS = 15000;

// Create the JWT token given the payload parameters. The signing secret
// defaults to NEXT_JWT_SECRET but can be overridden per facility (the target
// gateway trusts its own secret).
export function createJwtToken({ sub, role, iat, exp }: JwtParams, secret?: string): string {
  const signingSecret = secret ?? process.env.NEXT_JWT_SECRET;
  // Fail fast on a missing/blank secret rather than signing with an empty key.
  // Validate via trim() but sign with the original value (a gateway reading the
  // same env verbatim would not trim it).
  if (!signingSecret || signingSecret.trim() === "") {
    throw new Error("Missing JWT signing secret");
  }
  const payload = { sub, role, iat, exp };
  return jwt.sign(payload, signingSecret);
}

// Handles the fetching of objects from the gRPC REST gateway including creating
// authentication tokens.
export async function fetchObjectFromRestGateway(
  endpoint: string,
  method: string,
  body: string,
): Promise<NextResponse> {
  // Abort a stalled gateway so a hung backend can't pin request threads until
  // the platform-level timeout. Hoisted above try/catch so the timer is cleared
  // on every path (success, error, abort) in finally.
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), GATEWAY_TIMEOUT_MS);
  try {
    // Route to the gateway for the facility selected in the request cookie
    // (Cuebot Facility menu), with any runtime admin override applied. Falls
    // back to the default/legacy gateway when no per-facility config is present.
    // Resolution + JWT signing live inside the try so any failure here is
    // returned through this function's error envelope rather than thrown to the
    // caller (some routes call fetchObjectFromRestGateway directly).
    const { gatewayUrl, jwtSecret } = await getRequestFacilityTargetWithOverrides();
    if (!gatewayUrl) {
      throw new Error("No REST gateway configured for the selected facility");
    }
    const url = `${gatewayUrl}${endpoint}`;

    const jwtParams: JwtParams = {
      sub: "user-id", // Replace with a user id
      role: "user-role", // Replace with the user's role
      iat: Math.floor(Date.now() / 1000),
      exp: Math.floor(Date.now() / 1000) + 3600, // Expires in 1 hour
    };
    const jwtToken = createJwtToken(jwtParams, jwtSecret);

    const response = await fetch(url, {
      method: method,
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${jwtToken}`,
      },
      body: body,
      signal: controller.signal,
    });

    const responseBody = await response.text();
    if (!response.ok) {
      handleFetchError(response.status, responseBody);
    }

    return NextResponse.json({ data: JSON.parse(responseBody) }, { status: response.status });
  } catch (error) {
    console.error(`Fetch error: ${error}`);
    handleError(error);
    return NextResponse.json({ error: (error as Error).message }, { status: 500 });
  } finally {
    clearTimeout(timer);
  }
}

// Centralized route handler to fetch data and handle errors.
// Shorten a gRPC endpoint ("/job.JobInterface/GetJobs") to a compact,
// bounded metric label ("job.getjobs") so the API usage counter stays small.
function shortEndpoint(endpoint: string): string {
  const parts = endpoint.replace(/^\//, "").split("/");
  const iface = (parts[0] ?? "").split(".")[0] || "unknown";
  const method = (parts[1] ?? "").toLowerCase() || "unknown";
  return `${iface}.${method}`;
}

export async function handleRoute(
  method: string,
  endpoint: string,
  body: string,
  log = false,
): Promise<NextResponse> {
  // Usage metrics: time the call and record it per (short endpoint, status
  // class). Best-effort - metric failures must never affect the response.
  const startedAt = Date.now();
  const shortName = shortEndpoint(endpoint);
  let observed = false;
  const observe = (status: number) => {
    if (observed) return;
    observed = true;
    try {
      MetricsService.getInstance().recordApiRequest(
        shortName,
        status,
        (Date.now() - startedAt) / 1000,
      );
    } catch {
      // ignore - metrics must never affect the response
    }
  };

  try {
    const response = await fetchObjectFromRestGateway(endpoint, method, body);
    const responseData = await response.json();

    if (responseData.error) {
      observe(response.status >= 400 ? response.status : 500);
      throw new Error(responseData.error);
    }

    // Record the action in the CueWeb Audit trail. Reads are filtered out
    // inside auditGatewayCall; this is the single chokepoint every mutating
    // CueWeb action funnels through. Awaited so the entry is durably written
    // before we respond, but it can never throw (best-effort).
    await auditGatewayCall(endpoint, method, body, true);

    observe(response.status);
    return NextResponse.json({ data: responseData.data }, { status: response.status });
  } catch (error) {
    observe(500);
    handleError(error);
    await auditGatewayCall(endpoint, method, body, false, (error as Error).message);
    return NextResponse.json({ error: (error as Error).message }, { status: 500 });
  }
}

// Helper function to handle errors during fetch requests.
function handleFetchError(status: number, errorMessage: string): void {
  switch (status) {
    case 401:
      throw new Error(`Unauthorized request: ${errorMessage}`);
    case 404:
      throw new Error(`Resource not found: ${errorMessage}`);
    default:
      throw new Error(`Unexpected API error: ${errorMessage}`);
  }
}
