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

// Create a subscription for a show on an allocation. Request:
// { show, allocation_id, size, burst }. RPC: /show.ShowInterface/CreateSubscription.
export async function POST(request: NextRequest) {
  const endpoint = "/show.ShowInterface/CreateSubscription";
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
    !jsonBody.show ||
    typeof jsonBody.allocation_id !== 'string' ||
    jsonBody.allocation_id.length === 0
  ) {
    return NextResponse.json({ error: 'Invalid request body: show and allocation_id are required' }, { status: 400 });
  }

  const body = JSON.stringify(jsonBody);
  const response = await handleRoute(method, endpoint, body, true);
  const responseData = await response.json();

  if (!response.ok) {
    // Cuebot rejects a duplicate (show, allocation) pair with a raw
    // DuplicateKeyException / unique-constraint SQL error. Map it to a short,
    // user-facing message instead of surfacing the SQL dump in a toast.
    const raw = String(responseData?.error ?? "");
    const friendly = /duplicate key|c_subscription_uk|already exists/i.test(raw)
      ? "This show already has a subscription on that allocation."
      : responseData.error;
    return NextResponse.json({ error: friendly }, { status: response.status });
  }
  return NextResponse.json({ data: responseData.data }, { status: response.status });
}
