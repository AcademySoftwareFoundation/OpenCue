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

// Add a render partition to a job (CueGUI "Use Local Cores" - book a host's
// resources to the job). Request: { job, host, threads, max_cores,
// max_memory, max_gpu_memory, max_gpus, username }.
// RPC: /job.JobInterface/AddRenderPartition.
export async function POST(request: NextRequest) {
  const endpoint = "/job.JobInterface/AddRenderPartition";
  if (request.method !== 'POST') {
    return NextResponse.json({ error: 'Invalid method. Only POST is allowed.' }, { status: 405 });
  }
  let jsonBody: any;
  try {
    jsonBody = await request.json();
  } catch {
    return NextResponse.json({ error: 'Invalid JSON in request body' }, { status: 400 });
  }
  if (!jsonBody?.job || typeof jsonBody.host !== 'string' || !jsonBody.host) {
    return NextResponse.json({ error: 'Invalid request body: job and host required' }, { status: 400 });
  }
  const response = await handleRoute(request.method, endpoint, JSON.stringify(jsonBody), true);
  const responseData = await response.json();
  if (!response.ok) {
    // Cuebot only allows a local render partition on a NIMBY-locked host (the
    // workstation must be reserved for local use first). Surface that as a
    // clear message instead of the raw SpcueRuntimeException stack trace.
    const raw = String(responseData?.error ?? "");
    const friendly = /not NIMBY locked/i.test(raw)
      ? `Use Local Cores requires host "${jsonBody.host}" to be NIMBY-locked first ` +
        `(this reserves the workstation for local use). NIMBY-lock the host, then try again.`
      : responseData.error;
    return NextResponse.json({ error: friendly }, { status: response.status });
  }
  return NextResponse.json({ data: responseData.data }, { status: response.status });
}
