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

// The REST gateway returns a double-nested dictionary for show lookups:
// { shows: { shows: [ {Show 0}, {Show 1}, ... ] } }
// We unwrap to a flat array so callers receive [ {Show 0}, {Show 1}, ... ].
//
// GetShows lists every show known to Cuebot; for "active only" use the
// related ShowInterface/GetActiveShows endpoint.

export async function POST(request: NextRequest) {
  const endpoint = "/show.ShowInterface/GetShows";
  const method = request.method;
  if (method !== 'POST') {
    return NextResponse.json({ error: 'Invalid method. Only POST is allowed.' }, { status: 405 });
  }

  let parsed: unknown = {};
  try {
    parsed = await request.json();
  } catch {
    // Empty body is acceptable - GetShows takes no parameters.
  }
  const body = JSON.stringify(parsed ?? {});

  const response = await handleRoute(method, endpoint, body);
  const responseData = await response.json();

  // Preserve the upstream HTTP status. NextResponse.json defaults to 200
  // when the second argument is omitted, which would otherwise mask
  // gateway 4xx / 5xx responses behind a 200 envelope.
  if (!response.ok) {
    return NextResponse.json(
      { error: responseData?.error ?? "Failed to fetch shows", status: response.status },
      { status: response.status },
    );
  }
  const shows = responseData?.data?.shows?.shows ?? [];
  return NextResponse.json(
    { data: shows, status: responseData.status ?? response.status },
    { status: response.status },
  );
}
