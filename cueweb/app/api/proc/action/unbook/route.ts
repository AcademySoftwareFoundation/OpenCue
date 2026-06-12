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
  // ProcInterface.UnbookProcs unbooks every proc matching the search criteria;
  // kill=true also kills the running frames. The REST gateway exposes
  // ProcInterface (rest_gateway main.go RegisterProcInterfaceHandlerFromEndpoint
  // + generate_unbound_methods=true). The gateway path uses the proto package
  // prefix, which is `host` because host.proto declares `package host;`. This
  // was verified live against the running gateway: `/host.ProcInterface/...`
  // returns 200 while `/proc.ProcInterface/...` (the prefix the gateway's own
  // test scripts use) 404s.
  const endpoint = "/host.ProcInterface/UnbookProcs";
  const method = request.method;
  if (method !== 'POST') {
    return NextResponse.json({ error: 'Invalid method. Only POST is allowed.' }, { status: 405 });
  }

  // Guard against malformed JSON so callers see a 400 instead of the route
  // throwing and Next.js surfacing a generic 500.
  let jsonBody: any;
  try {
    jsonBody = await request.json();
  } catch {
    return NextResponse.json({ error: 'Invalid JSON body' }, { status: 400 });
  }
  // Body is { r: ProcSearchCriteria, kill: boolean }: r carries the proc search
  // criteria (e.g. { jobs: [...] } for a job-scoped unbook) and kill decides
  // whether matching frames are killed as they are unbooked.
  if (
    !jsonBody
    || typeof jsonBody !== 'object'
    || Array.isArray(jsonBody)
    || !jsonBody.r
    || typeof jsonBody.kill !== 'boolean'
  ) {
    return NextResponse.json({ error: 'Invalid request body (need {r, kill:boolean})' }, { status: 400 });
  }

  const body = JSON.stringify(jsonBody);
  const response = await handleRoute(method, endpoint, body, true);
  const responseData = await response.json();

  if (!response.ok) return NextResponse.json({ error: responseData.error }, { status: response.status });
  return NextResponse.json({ data: responseData.data }, { status: response.status });
}
