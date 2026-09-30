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

export async function POST(request: NextRequest) {
  const endpoint = "/job.JobInterface/SetMinCores";
  const method = request.method;
  if (method !== 'POST') {
    return NextResponse.json({ error: 'Invalid method. Only POST is allowed.' }, { status: 405 });
  }

  let jsonBody: any;
  try {
    jsonBody = await request.json();
  } catch {
    return NextResponse.json({ error: 'Invalid JSON body' }, { status: 400 });
  }
  if (
    !jsonBody
    || typeof jsonBody !== 'object'
    || Array.isArray(jsonBody)
    || !jsonBody.job
    || typeof jsonBody.val !== 'number'
  ) {
    return NextResponse.json({ error: 'Invalid request body (need {job, val:number})' }, { status: 400 });
  }

  if (!Number.isFinite(jsonBody.val) || jsonBody.val < 0 || jsonBody.val > 50000) {
    return NextResponse.json({ error: 'val must be a number between 0 and 50000' }, { status: 400 });
  }

  const body = JSON.stringify(jsonBody);
  const response = await handleRoute(method, endpoint, body, true);
  const responseData = await response.json();

  if (!response.ok) return NextResponse.json({ error: responseData.error }, { status: response.status });
  return NextResponse.json({ data: responseData.data }, { status: response.status });
}
