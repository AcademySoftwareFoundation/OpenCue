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
  const endpoint = "/show.ShowInterface/FindShow";
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
  if (!jsonBody || typeof jsonBody !== 'object' || !jsonBody.name) {
    return NextResponse.json({ error: 'Invalid request body: name is required' }, { status: 400 });
  }

  const body = JSON.stringify(jsonBody);
  const response = await handleRoute(method, endpoint, body);
  const responseData = await response.json();

  if (!response.ok) {
    // An unknown show comes back as a not-found error -> report { notFound }.
    // Any other error is a real failure, so keep its status instead of
    // reporting the name as available.
    const message = String(responseData?.error ?? "");
    if (/not\s*found/i.test(message)) {
      return NextResponse.json({ notFound: true }, { status: 200 });
    }
    return NextResponse.json({ error: responseData.error }, { status: response.status });
  }
  return NextResponse.json({ data: responseData.data }, { status: response.status });
}
