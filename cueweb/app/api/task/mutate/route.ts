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

// Consolidated proxy for the Task Properties dialog mutations (CueGUI
// TasksDialog). Body is { op, ...payload }; `op` selects one of the allowlisted
// Department / Task RPCs and the rest is forwarded verbatim.
const ENDPOINTS: Record<string, string> = {
  // DepartmentInterface
  "dept.addtask": "/department.DepartmentInterface/AddTask",
  "dept.setmanagedcores": "/department.DepartmentInterface/SetManagedCores",
  "dept.enabletimanaged": "/department.DepartmentInterface/EnableTiManaged",
  "dept.disabletimanaged": "/department.DepartmentInterface/DisableTiManaged",
  // TaskInterface
  "task.setmincores": "/task.TaskInterface/SetMinCores",
  "task.clearadjustments": "/task.TaskInterface/ClearAdjustments",
  "task.delete": "/task.TaskInterface/Delete",
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
    return NextResponse.json({ error: `Unknown task op: ${op}` }, { status: 400 });
  }

  const response = await handleRoute(method, endpoint, JSON.stringify(payload), true);
  const responseData = await response.json();
  if (!response.ok) {
    return NextResponse.json({ error: responseData?.error ?? `Failed: ${op}` }, { status: response.status });
  }
  return NextResponse.json({ data: responseData.data ?? { success: true } }, { status: response.status });
}
