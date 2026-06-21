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

// Set a layer's minimum cores (CueGUI Stuck Frame "Core Up"). Request:
// { layer, cores }. RPC: /job.LayerInterface/SetMinCores.
export async function POST(request: NextRequest) {
  const endpoint = "/job.LayerInterface/SetMinCores";
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
  // cores is a float proto field (fractional core counts are valid), so reject
  // only non-finite (typeof NaN is "number") and negative values, not fractions.
  if (
    !jsonBody ||
    typeof jsonBody !== 'object' ||
    typeof jsonBody.layer !== 'object' ||
    jsonBody.layer === null ||
    typeof jsonBody.layer.id !== 'string' ||
    jsonBody.layer.id.trim() === '' ||
    typeof jsonBody.cores !== 'number' ||
    !Number.isFinite(jsonBody.cores) ||
    jsonBody.cores < 0
  ) {
    return NextResponse.json({ error: 'Invalid request body: layer.id and non-negative numeric cores are required' }, { status: 400 });
  }

  const body = JSON.stringify(jsonBody);
  const response = await handleRoute(method, endpoint, body, true);
  const responseData = await response.json();

  if (!response.ok) return NextResponse.json({ error: responseData.error }, { status: response.status });
  return NextResponse.json({ data: responseData.data }, { status: response.status });
}
