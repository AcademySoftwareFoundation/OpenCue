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

// Lists the subscriptions for a single show (the per-show table on the
// Subscriptions page, mirroring CueGUI's SubscriptionsWidget which calls
// show.getSubscriptions()). Request: { show }. The gateway double-nests the
// result as { subscriptions: { subscriptions: [...] } }; we unwrap to a flat
// array. RPC: /show.ShowInterface/GetSubscriptions.
export async function POST(request: NextRequest) {
  const endpoint = "/show.ShowInterface/GetSubscriptions";
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
  if (!jsonBody || typeof jsonBody !== 'object' || !jsonBody.show) {
    return NextResponse.json({ error: 'Invalid request body: show is required' }, { status: 400 });
  }

  const body = JSON.stringify(jsonBody);
  const response = await handleRoute(method, endpoint, body);
  const responseData = await response.json();

  if (!response.ok) {
    return NextResponse.json(
      { error: responseData?.error ?? "Failed to fetch subscriptions" },
      { status: response.status },
    );
  }
  const subscriptions = responseData?.data?.subscriptions?.subscriptions ?? [];
  return NextResponse.json({ data: subscriptions }, { status: response.status });
}
