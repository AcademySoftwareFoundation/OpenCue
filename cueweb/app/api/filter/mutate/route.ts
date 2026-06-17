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

// Consolidated proxy for the View Filters dialog mutations. The body is
// { op, ...payload }; `op` selects one of the allowlisted Filter / Matcher /
// Action RPCs and the rest of the body is forwarded verbatim. Returns the
// gateway response data (the created object for create ops).
const ENDPOINTS: Record<string, string> = {
  // ShowInterface
  "show.createfilter": "/show.ShowInterface/CreateFilter",
  // FilterInterface
  "filter.setname": "/filter.FilterInterface/SetName",
  "filter.settype": "/filter.FilterInterface/SetType",
  "filter.setenabled": "/filter.FilterInterface/SetEnabled",
  "filter.setorder": "/filter.FilterInterface/SetOrder",
  "filter.raiseorder": "/filter.FilterInterface/RaiseOrder",
  "filter.lowerorder": "/filter.FilterInterface/LowerOrder",
  "filter.orderfirst": "/filter.FilterInterface/OrderFirst",
  "filter.orderlast": "/filter.FilterInterface/OrderLast",
  "filter.delete": "/filter.FilterInterface/Delete",
  "filter.creatematcher": "/filter.FilterInterface/CreateMatcher",
  "filter.createaction": "/filter.FilterInterface/CreateAction",
  // MatcherInterface
  "matcher.commit": "/filter.MatcherInterface/Commit",
  "matcher.delete": "/filter.MatcherInterface/Delete",
  // ActionInterface
  "action.commit": "/filter.ActionInterface/Commit",
  "action.delete": "/filter.ActionInterface/Delete",
};

export async function POST(request: NextRequest) {
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
  const { op, ...payload } = jsonBody ?? {};
  const endpoint = typeof op === 'string' ? ENDPOINTS[op] : undefined;
  if (!endpoint) {
    return NextResponse.json({ error: `Unknown filter op: ${op}` }, { status: 400 });
  }

  const response = await handleRoute(method, endpoint, JSON.stringify(payload), true);
  const responseData = await response.json();
  if (!response.ok) {
    return NextResponse.json({ error: responseData?.error ?? `Failed: ${op}` }, { status: response.status });
  }
  return NextResponse.json({ data: responseData.data ?? { success: true } }, { status: response.status });
}
