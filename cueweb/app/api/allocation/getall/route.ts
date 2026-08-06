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

// Lists every allocation (for the subscription allocation dropdowns). The
// gateway double-nests the result as { allocations: { allocations: [...] } };
// we unwrap to a flat array. RPC: /facility.AllocationInterface/GetAll.
export async function POST(request: NextRequest) {
  const endpoint = "/facility.AllocationInterface/GetAll";
  const method = request.method;
  if (method !== 'POST') {
    return NextResponse.json({ error: 'Invalid method. Only POST is allowed.' }, { status: 405 });
  }

  let parsed: unknown = {};
  try {
    parsed = await request.json();
  } catch {
    // Empty body is acceptable - GetAll takes no parameters.
  }
  const body = JSON.stringify(parsed ?? {});

  const response = await handleRoute(method, endpoint, body);
  const responseData = await response.json();

  if (!response.ok) {
    return NextResponse.json(
      { error: responseData?.error ?? "Failed to fetch allocations" },
      { status: response.status },
    );
  }
  const allocations = responseData?.data?.allocations?.allocations ?? [];
  return NextResponse.json({ data: allocations }, { status: response.status });
}
