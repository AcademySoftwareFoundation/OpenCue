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

// The REST gateway returns a double-nested dictionary for host lookups:
// { hosts: { hosts: [ {Host 0}, {Host 1}, ... ] } }
// We unwrap to a flat array so callers receive [ {Host 0}, {Host 1}, ... ].

export async function POST(request: NextRequest) {
  const endpoint = "/host.HostInterface/GetHosts";
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
  if (!jsonBody || typeof jsonBody !== 'object' || Array.isArray(jsonBody)) {
    return NextResponse.json({ error: 'Invalid request body' }, { status: 400 });
  }
  const body = JSON.stringify(jsonBody);

  const response = await handleRoute(method, endpoint, body);
  // The REST gateway is supposed to return JSON, but a misconfigured or down
  // gateway / proxy can answer with empty bodies / HTML / plain text. Read
  // the raw text and parse defensively so a non-JSON upstream surfaces as a
  // proper upstream error instead of crashing the route with a 500.
  const raw = await response.text();
  let responseData: any = {};
  let parseFailed = false;
  if (raw) {
    try {
      responseData = JSON.parse(raw);
    } catch {
      parseFailed = true;
      responseData = { error: raw };
    }
  }
  // A non-JSON body on an otherwise-OK upstream response is itself an
  // upstream outage (HTML error page, plain-text proxy notice, ...) -
  // surface it as a 502 instead of silently returning an empty host
  // list and hiding the failure as "no hosts".
  if (response.ok && parseFailed) {
    return NextResponse.json(
      { error: responseData.error ?? 'Upstream returned a non-JSON response', status: 502 },
      { status: 502 },
    );
  }

  // Preserve the upstream HTTP status. NextResponse.json defaults to 200
  // when the second argument is omitted, which would otherwise mask
  // gateway 4xx / 5xx responses behind a 200 envelope.
  if (!response.ok) {
    return NextResponse.json(
      { error: responseData.error, status: response.status },
      { status: response.status },
    );
  }
  const hosts = responseData?.data?.hosts?.hosts ?? [];
  return NextResponse.json(
    { data: hosts, status: responseData.status ?? response.status },
    { status: response.status },
  );
}
