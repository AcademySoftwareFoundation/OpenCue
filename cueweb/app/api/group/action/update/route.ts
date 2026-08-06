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

// Apply a Group Properties edit. Request: { group, changes: {...} }. Each
// present field maps to one GroupInterface setter RPC (matching CueGUI's
// GroupDialog, which only calls the setters whose value changed). Cores are
// decimal cores; priority and gpus are integers.
//
// changes keys -> RPC + request field:
//   name                 SetName               { group, name }
//   department           SetDepartment         { group, dept }
//   defaultJobPriority   SetDefaultJobPriority { group, priority }
//   defaultJobMinCores   SetDefaultJobMinCores { group, min_cores }
//   defaultJobMaxCores   SetDefaultJobMaxCores { group, max_cores }
//   minCores             SetMinCores           { group, min_cores }
//   maxCores             SetMaxCores           { group, max_cores }
//   defaultJobMinGpus    SetDefaultJobMinGpus  { group, min_gpus }
//   defaultJobMaxGpus    SetDefaultJobMaxGpus  { group, max_gpus }
//   minGpus              SetMinGpus            { group, min_gpus }
//   maxGpus              SetMaxGpus            { group, max_gpus }

type Setter = { rpc: string; field: string };

const SETTERS: Record<string, Setter> = {
  name: { rpc: "SetName", field: "name" },
  department: { rpc: "SetDepartment", field: "dept" },
  defaultJobPriority: { rpc: "SetDefaultJobPriority", field: "priority" },
  defaultJobMinCores: { rpc: "SetDefaultJobMinCores", field: "min_cores" },
  defaultJobMaxCores: { rpc: "SetDefaultJobMaxCores", field: "max_cores" },
  minCores: { rpc: "SetMinCores", field: "min_cores" },
  maxCores: { rpc: "SetMaxCores", field: "max_cores" },
  defaultJobMinGpus: { rpc: "SetDefaultJobMinGpus", field: "min_gpus" },
  defaultJobMaxGpus: { rpc: "SetDefaultJobMaxGpus", field: "max_gpus" },
  minGpus: { rpc: "SetMinGpus", field: "min_gpus" },
  maxGpus: { rpc: "SetMaxGpus", field: "max_gpus" },
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
  const group = jsonBody?.group;
  const changes = jsonBody?.changes;
  if (!group?.id || !changes || typeof changes !== 'object') {
    return NextResponse.json({ error: 'Invalid request body: group and changes are required' }, { status: 400 });
  }

  // Reject unknown keys rather than silently dropping them: a no-op that still
  // reports success would hide a contract regression (e.g. a renamed setter key)
  // and the user's edit would appear to apply when it did not.
  const unknownKeys = Object.keys(changes).filter((key) => !(key in SETTERS));
  if (unknownKeys.length > 0) {
    return NextResponse.json(
      { error: `Unknown change keys: ${unknownKeys.join(", ")}` },
      { status: 400 },
    );
  }

  // Apply each changed field in turn; stop and report the first failure so the
  // dialog can keep the modal open for retry.
  for (const key of Object.keys(changes)) {
    const setter = SETTERS[key];
    const value = changes[key];
    const isName = setter.field === "name" || setter.field === "dept";
    if (isName) {
      if (typeof value !== 'string') {
        return NextResponse.json({ error: `Invalid value for ${key}` }, { status: 400 });
      }
    } else if (typeof value !== 'number' || !Number.isFinite(value)) {
      return NextResponse.json({ error: `Invalid value for ${key}` }, { status: 400 });
    }

    const endpoint = `/job.GroupInterface/${setter.rpc}`;
    const body = JSON.stringify({ group, [setter.field]: value });
    const response = await handleRoute(method, endpoint, body, true);
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      return NextResponse.json(
        { error: data?.error ?? `Failed to apply ${key}` },
        { status: response.status },
      );
    }
  }

  return NextResponse.json({ data: { success: true } }, { status: 200 });
}
