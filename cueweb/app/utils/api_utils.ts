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

import jwt from "jsonwebtoken";
import { NextResponse } from "next/server";
import { handleError } from "./notify_utils";
import { getRequestFacilityTarget } from "@/lib/facility";

/************************************************************/
// Utility functions for accessing the Api including:
// - helping functions fetch objects from the REST gateway
// - creating jwt tokens used to access the REST gateway
// - accessing action api's which return success or failure
// - accessing get api's which return objects
/************************************************************/

interface JwtParams {
  sub: string;
  role: string;
  iat: number;
  exp: number;
}

// Handles the fetching of objects from the gRPC REST gateway including creating authentication tokens
export async function fetchObjectFromRestGateway(
    endpoint: string,
    method: string,
    body: string
  ): Promise<NextResponse> {
    // Route to the gateway for the facility selected in the request cookie
    // (Cuebot Facility menu). Falls back to the default/legacy gateway when
    // no per-facility config is present.
    const { gatewayUrl, jwtSecret } = await getRequestFacilityTarget();
    if (!gatewayUrl) {
      // Misconfigured facility (no gateway URL and no default): fail with a
      // clear, diagnosable error instead of a generic fetch failure.
      return NextResponse.json(
        { error: "No REST gateway configured for the selected facility" },
        { status: 503 },
      );
    }
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
  

// Helper function to access a post API with a success or failure returned and handle any errors.
// Actions follow this format: post to the API and see if the action was successful
export async function accessActionApi(endpoint: string, body: string | string[]): Promise<{ success?: boolean; error?: string }> {
    // Default to a same-origin relative URL when NEXT_PUBLIC_URL is empty
    // or unset. The API routes are mounted by this same Next.js app, so
    // the browser can reach them at whatever origin the page loaded from
    // (e.g. http://localhost:3000 on the dev environment, http://<lan-ip>:3000
    // from another device on the same network). Hardcoding the host in the
    // client bundle would break every non-localhost client.
    const base = process.env.NEXT_PUBLIC_URL ?? "";
    const bodyAr = Array.isArray(body) ? body : [body];

    try {
      // Run all API requests in parallel for better performance
      await Promise.all(
        bodyAr.map(async (curBody) => {
          const response = await fetch(`${base}${endpoint}`, {
            method: "POST",
            headers: { "Content-Type": "application/x-www-form-urlencoded" },
            body: curBody,
          });
          const res = await response.json();

          if (res.error) {
            throw new Error(res.error);
          }
        })
      );
      return { success: true };
    } catch (error) {
      handleError(error, `Error at ${endpoint}`);
      return { error: (error as Error).message };
    }
  }
  

// Helper function to access object retrieval APIs that return arrays of objects (jobs, layers, or frames).
export async function accessGetApi(endpoint: string, body: string): Promise<any> {
    // Same-origin relative URL by default (see accessActionApi above).
    const base = process.env.NEXT_PUBLIC_URL ?? "";

    try {
      const response = await fetch(`${base}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: body,
      });
      const res = await response.json();
  
      if (res.error) {
        throw new Error(res.error);
      }
      return res.data;
    } catch (error) {
      handleError(error, `Error at ${endpoint}`);
      return null;
    }
  }
  

// Centralized route handler to fetch data and handle errors
export async function handleRoute(
    method: string,
    endpoint: string,
    body: string,
    log = false
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

// Helper function to handle errors during fetch requests
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
  