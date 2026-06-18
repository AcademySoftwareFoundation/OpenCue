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

interface JwtParams {
  sub: string;
  role: string;
  iat: number;
  exp: number;
}

// Create the JWT token given the payload parameters. The signing secret
// defaults to NEXT_JWT_SECRET but can be overridden per facility (the target
// gateway trusts its own secret).
export function createJwtToken({ sub, role, iat, exp }: JwtParams, secret?: string): string {
  const signingSecret = secret ?? process.env.NEXT_JWT_SECRET;
  const payload = { sub, role, iat, exp };
  return jwt.sign(payload, signingSecret as string);
}

// Handles the fetching of objects from the gRPC REST gateway including creating
// authentication tokens.
export async function fetchObjectFromRestGateway(
  endpoint: string,
  method: string,
  body: string,
): Promise<NextResponse> {
  // Route to the gateway for the facility selected in the request cookie
  // (Cuebot Facility menu), with any runtime admin override applied. Falls
  // back to the default/legacy gateway when no per-facility config is present.
  const { gatewayUrl, jwtSecret } = await getRequestFacilityTargetWithOverrides();
  const url = `${gatewayUrl}${endpoint}`;

  const jwtParams: JwtParams = {
    sub: "user-id", // Replace with a user id
    role: "user-role", // Replace with the user's role
    iat: Math.floor(Date.now() / 1000),
    exp: Math.floor(Date.now() / 1000) + 3600, // Expires in 1 hour
  };
  const jwtToken = createJwtToken(jwtParams, jwtSecret);

  try {
    const response = await fetch(url, {
      method: method,
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${jwtToken}`,
      },
      body: body,
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
  }
}

// Centralized route handler to fetch data and handle errors.
export async function handleRoute(
  method: string,
  endpoint: string,
  body: string,
  log = false,
): Promise<NextResponse> {
  try {
    const response = await fetchObjectFromRestGateway(endpoint, method, body);
    const responseData = await response.json();

    if (responseData.error) {
      throw new Error(responseData.error);
    }

    return NextResponse.json({ data: responseData.data }, { status: response.status });
  } catch (error) {
    handleError(error);
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
