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

// List a show's service overrides (Service Properties dialog). Request:
// { show }. RPC: /show.ShowInterface/GetServiceOverrides. The gateway nests the
// seq under serviceOverrides.serviceOverrides.
export async function POST(request: NextRequest) {
  const endpoint = "/show.ShowInterface/GetServiceOverrides";
  const method = request.method;
  if (method !== 'POST') {
    return NextResponse.json({ error: 'Invalid method. Only POST is allowed.' }, { status: 405 });
  }

  let jsonBody: any;
  try {
    jsonBody = await request.json();
  } catch {
    return NextResponse.json({ error: 'Invalid JSON in request body' }, { status: 400 });
  }
  const body = JSON.stringify(jsonBody);
  if (!jsonBody || typeof jsonBody !== 'object' || !jsonBody.show?.id) {
    return NextResponse.json({ error: 'Invalid request body: show is required' }, { status: 400 });
  }

  const response = await handleRoute(method, endpoint, body);
  const responseData = await response.json();
  if (!response.ok) return NextResponse.json({ error: responseData.error }, { status: response.status });
  return NextResponse.json(
    { data: responseData.data?.serviceOverrides?.serviceOverrides ?? [] },
    { status: response.status },
  );
}
