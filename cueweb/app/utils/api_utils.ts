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

import { handleError } from "./notify_utils";

/************************************************************/
// Client-safe API helpers (same-origin calls to this app's own /api routes).
//
// The server-only gateway helpers (createJwtToken, fetchObjectFromRestGateway,
// handleRoute) live in `gateway_server.ts`. They were split out of this file so
// the filesystem-backed facility override store stays out of the client bundle
// (this module is reachable from client components via get_utils/action_utils).
/************************************************************/

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
