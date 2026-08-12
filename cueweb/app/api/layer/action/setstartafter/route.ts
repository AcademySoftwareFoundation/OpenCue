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

// Defer booking of a layer until a chosen time (CueGUI LayerStartAfterDialog).
// RPC: /job.LayerInterface/SetStartAfter.
// Request: { layer, start_after: number (UTC epoch seconds, 0 clears), username }.
//
// Cuebot rejects anything negative or more than five years out as
// INVALID_ARGUMENT, on the theory that such a value is milliseconds passed
// where seconds are expected. The same bound is applied here so an obviously
// wrong value never reaches the gateway; the exact limit stays Cuebot's call.
const MAX_FUTURE_SECONDS = 5 * 365 * 24 * 3600;

export async function POST(request: NextRequest) {
  const endpoint = "/job.LayerInterface/SetStartAfter";
  if (request.method !== 'POST') {
    return NextResponse.json({ error: 'Invalid method. Only POST is allowed.' }, { status: 405 });
  }

  let jsonBody: any;
  try {
    jsonBody = await request.json();
  } catch {
    return NextResponse.json({ error: 'Invalid JSON body' }, { status: 400 });
  }

  if (!jsonBody?.layer || !Number.isInteger(jsonBody.start_after)) {
    return NextResponse.json(
      { error: 'Invalid request body (need {layer, start_after:integer})' },
      { status: 400 },
    );
  }
  if (jsonBody.start_after < 0 || jsonBody.start_after > Math.floor(Date.now() / 1000) + MAX_FUTURE_SECONDS) {
    return NextResponse.json(
      {
        error:
          'start_after must be a Unix timestamp in seconds no more than 5 years in the ' +
          'future, or 0 to clear the delay. Was a milliseconds value passed?',
      },
      { status: 400 },
    );
  }

  const response = await handleRoute(request.method, endpoint, JSON.stringify(jsonBody), true);
  const responseData = await response.json();
  if (!response.ok) return NextResponse.json({ error: responseData.error }, { status: response.status });
  return NextResponse.json({ data: responseData.data }, { status: response.status });
}
