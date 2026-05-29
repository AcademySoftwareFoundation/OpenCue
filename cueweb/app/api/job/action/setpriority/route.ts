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

export async function POST(request: NextRequest) {
  const endpoint = "/job.JobInterface/SetPriority";
  const method = request.method;
  if (method !== 'POST') {
    return NextResponse.json({ error: 'Invalid method. Only POST is allowed.' }, { status: 405 });
  }

  // Guard against malformed JSON so callers see a 400 instead of the route
  // throwing and Next.js surfacing a generic 500 - request.json() throws a
  // SyntaxError on invalid input.
  let jsonBody: unknown;
  try {
    jsonBody = await request.json();
  } catch {
    return NextResponse.json({ error: 'Invalid JSON body' }, { status: 400 });
  }
  if (
    !jsonBody
    || typeof jsonBody !== 'object'
    || Array.isArray(jsonBody)
    || !(jsonBody as { job?: unknown }).job
    || typeof (jsonBody as { val?: unknown }).val !== 'number'
  ) {
    return NextResponse.json({ error: 'Invalid request body (need {job, val:number})' }, { status: 400 });
  }
  const body = JSON.stringify(jsonBody);

  const response = await handleRoute(method, endpoint, body, true);
  const responseData = await response.json();
  // Preserve the upstream HTTP status. NextResponse.json defaults to 200
  // when the second argument is omitted, which would otherwise mask
  // gateway 4xx / 5xx responses behind a 200 envelope.
  if (!response.ok) {
    return NextResponse.json(
      { error: responseData.error, status: response.status },
      { status: response.status },
    );
  }
  return NextResponse.json(
    { data: responseData.data, status: responseData.status ?? response.status },
    { status: response.status },
  );
}
