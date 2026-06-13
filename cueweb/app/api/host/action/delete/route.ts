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

import { handleRoute } from '@/app/utils/api_utils';
import { NextRequest, NextResponse } from "next/server";

// Delete a host (CueGUI "Delete Host", admin-only). Request: { host }.
// RPC: /host.HostInterface/Delete.
export async function POST(request: NextRequest) {
  const endpoint = "/host.HostInterface/Delete";
  if (request.method !== 'POST') {
    return NextResponse.json({ error: 'Invalid method. Only POST is allowed.' }, { status: 405 });
  }
  let jsonBody: any;
  try {
    jsonBody = await request.json();
  } catch {
    return NextResponse.json({ error: 'Invalid JSON in request body' }, { status: 400 });
  }
  if (!jsonBody?.host) {
    return NextResponse.json({ error: 'Invalid request body: host required' }, { status: 400 });
  }
  // handleRoute already returns the final {data}/{error} NextResponse; return it
  // directly so error propagation and status codes are preserved.
  return handleRoute(request.method, endpoint, JSON.stringify(jsonBody), true);
}
