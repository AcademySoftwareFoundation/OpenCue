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

// Set a subscription's size. Request: { subscription, new_size }. `new_size` is
// in centcores (cores * 100) - the caller converts, matching CueGUI's
// int(value * 100.0). RPC: /subscription.SubscriptionInterface/SetSize.
export async function POST(request: NextRequest) {
  const endpoint = "/subscription.SubscriptionInterface/SetSize";
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
    !jsonBody.subscription ||
    typeof jsonBody.new_size !== 'number' ||
    !Number.isFinite(jsonBody.new_size) ||
    jsonBody.new_size < 0
  ) {
    return NextResponse.json(
      { error: 'Invalid request body: subscription and a non-negative new_size are required' },
      { status: 400 },
    );
  }

  const body = JSON.stringify(jsonBody);
  const response = await handleRoute(method, endpoint, body, true);
  const responseData = await response.json();

  if (!response.ok) return NextResponse.json({ error: responseData.error }, { status: response.status });
  return NextResponse.json({ data: responseData.data }, { status: response.status });
}
