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

// Replace a layer's tags. Request: { layer, tags: string[] }. SetTags is a
// wholesale replace (not add/remove), so the client sends the full desired
// set. Cuebot rejects an empty tag set, and CueGUI requires at least one
// tag, so we guard for a non-empty array here too. RPC:
// /job.LayerInterface/SetTags (LayerSetTagsRequest).
export async function POST(request: NextRequest) {
  const endpoint = "/job.LayerInterface/SetTags";
  const method = request.method;
  if (method !== 'POST') {
    return NextResponse.json({ error: 'Invalid method. Only POST is allowed.' }, { status: 405 });
  }

  let jsonBody: any;
  try {
    jsonBody = await request.json();
  } catch {
    return NextResponse.json({ error: 'Invalid JSON body' }, { status: 400 });
  }
  if (
    !jsonBody
    || typeof jsonBody !== 'object'
    || Array.isArray(jsonBody)
    || !jsonBody.layer
    || !Array.isArray(jsonBody.tags)
  ) {
    return NextResponse.json({ error: 'Invalid request body (need {layer, tags:string[]})' }, { status: 400 });
  }

  if (jsonBody.tags.length === 0 || !jsonBody.tags.every((t: unknown) => typeof t === 'string' && t.trim() !== '')) {
    return NextResponse.json({ error: 'tags must be a non-empty array of non-empty strings' }, { status: 400 });
  }

  const body = JSON.stringify(jsonBody);
  const response = await handleRoute(method, endpoint, body, true);
  const responseData = await response.json();

  if (!response.ok) return NextResponse.json({ error: responseData.error }, { status: response.status });
  return NextResponse.json({ data: responseData.data }, { status: response.status });
}
