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

// Set a limit's max value. Request: { name, max_value }. The value must be a
// non-negative integer. RPC: /limit.LimitInterface/SetMaxValue.
export async function POST(request: NextRequest) {
  const endpoint = "/limit.LimitInterface/SetMaxValue";
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
  if (
    !jsonBody ||
    typeof jsonBody !== 'object' ||
    typeof jsonBody.name !== 'string' ||
    jsonBody.name.length === 0 ||
    typeof jsonBody.max_value !== 'number' ||
    jsonBody.max_value < 0
  ) {
    return NextResponse.json({ error: 'Invalid request body: name and a non-negative max_value are required' }, { status: 400 });
  }

  const body = JSON.stringify({ name: jsonBody.name, max_value: jsonBody.max_value });
  const response = await handleRoute(method, endpoint, body, true);
  const responseData = await response.json();

  if (!response.ok) return NextResponse.json({ error: responseData.error }, { status: response.status });
  return NextResponse.json({ data: responseData.data }, { status: response.status });
}
