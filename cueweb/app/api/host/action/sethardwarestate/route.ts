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

import { handleRoute } from '@/app/utils/gateway_server';
import { NextRequest, NextResponse } from "next/server";

// Set a host's hardware state (CueGUI "Set/Clear Repair State"). Request:
// { host, state } where state is a HardwareState enum name (e.g. "REPAIR",
// "DOWN", "UP"). RPC: /host.HostInterface/SetHardwareState.
export async function POST(request: NextRequest) {
  const endpoint = "/host.HostInterface/SetHardwareState";
  if (request.method !== 'POST') {
    return NextResponse.json({ error: 'Invalid method. Only POST is allowed.' }, { status: 405 });
  }
  let jsonBody: any;
  try {
    jsonBody = await request.json();
  } catch {
    return NextResponse.json({ error: 'Invalid JSON in request body' }, { status: 400 });
  }
  if (!jsonBody?.host || typeof jsonBody.state !== 'string') {
    return NextResponse.json({ error: 'Invalid request body: host and state required' }, { status: 400 });
  }
  // state must be a host.HardwareState enum name (proto/src/host.proto).
  const VALID_STATES = ["UP", "DOWN", "REBOOTING", "REBOOT_WHEN_IDLE", "REPAIR"];
  if (!VALID_STATES.includes(jsonBody.state)) {
    return NextResponse.json(
      { error: `Invalid state: must be one of ${VALID_STATES.join(", ")}` },
      { status: 400 },
    );
  }
  // handleRoute already returns the final {data}/{error} NextResponse; return it
  // directly so error propagation and status codes are preserved.
  return handleRoute(request.method, endpoint, JSON.stringify(jsonBody), true);
}
