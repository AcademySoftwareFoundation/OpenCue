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

import { fetchObjectFromRestGateway } from '@/app/utils/api_utils';
import { NextRequest, NextResponse } from "next/server";

// Mirrors Job.getWhatDependsOnThis (pycue) ->
// JobInterface.GetWhatDependsOnThis. Returns the depend.DependSeq for
// every depend where `depend_on_job` is the supplied job - i.e. every
// other job that is currently blocked on this one. Used by the
// Cuetopia Group-By "Dependent" tree view to find each job's children.
export async function POST(request: NextRequest) {
  const endpoint = "/job.JobInterface/GetWhatDependsOnThis";
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
  if (!jsonBody || typeof jsonBody !== 'object' || Array.isArray(jsonBody) || !jsonBody.job) {
    return NextResponse.json({ error: 'Invalid request body (need {job})' }, { status: 400 });
  }

  const response = await fetchObjectFromRestGateway(endpoint, method, JSON.stringify(jsonBody));
  const responseData = await response.json();
  if (!response.ok) {
    return NextResponse.json(
      { error: responseData?.error ?? 'Upstream error' },
      { status: response.status },
    );
  }
  return NextResponse.json({ data: responseData.data }, { status: response.status });
}
