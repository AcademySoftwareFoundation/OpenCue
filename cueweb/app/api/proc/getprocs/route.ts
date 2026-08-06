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

// List procs matching a ProcSearchCriteria (the Monitor Hosts proc panel,
// filtered by host names). Request: { r: { hosts: [...] } }. The gateway
// double-nests as { procs: { procs: [...] } }; we unwrap to a flat array.
// RPC: /host.ProcInterface/GetProcs.
export async function POST(request: NextRequest) {
  const endpoint = "/host.ProcInterface/GetProcs";
  if (request.method !== 'POST') {
    return NextResponse.json({ error: 'Invalid method. Only POST is allowed.' }, { status: 405 });
  }
  let jsonBody: any;
  try {
    jsonBody = await request.json();
  } catch {
    return NextResponse.json({ error: 'Invalid JSON in request body' }, { status: 400 });
  }
  if (!jsonBody?.r || typeof jsonBody.r !== 'object') {
    return NextResponse.json({ error: 'Invalid request body: r (ProcSearchCriteria) required' }, { status: 400 });
  }
  const response = await handleRoute(request.method, endpoint, JSON.stringify(jsonBody));
  const responseData = await response.json();
  if (!response.ok) {
    return NextResponse.json({ error: responseData?.error ?? "Failed to fetch procs" }, { status: response.status });
  }
  const procs = responseData?.data?.procs?.procs ?? [];
  return NextResponse.json({ data: procs }, { status: response.status });
}
