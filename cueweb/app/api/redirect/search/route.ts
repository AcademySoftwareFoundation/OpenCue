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

import { fetchObjectFromRestGateway } from '@/app/utils/gateway_server';
import { NextRequest, NextResponse } from "next/server";

// Server-side search for the Redirect tool (CueGUI Redirect.update()). Lists
// the procs for a show+allocations (ProcInterface.GetProcs), filters them
// (target job, already-redirected, exclude regex, required service, included
// groups), groups them by host, looks up each host's idle cores/memory
// (FindHost) and the source job's reserved cores / waiting frames (GetJobs),
// then keeps hosts whose totals satisfy the core/memory/runtime thresholds -
// up to the result limit.
//
// RPCs: /host.ProcInterface/GetProcs, /host.HostInterface/FindHost,
//       /job.JobInterface/GetJobs.

const NOW = () => Math.floor(Date.now() / 1000);

async function gatewayJson(endpoint: string, body: string): Promise<any | null> {
  try {
    const resp = await fetchObjectFromRestGateway(endpoint, "POST", body);
    const json = await resp.json();
    if (json?.error) return null;
    return json?.data ?? null;
  } catch {
    return null;
  }
}

export async function POST(request: NextRequest) {
  let p: any;
  try {
    p = await request.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON in request body" }, { status: 400 });
  }
  const show: string = p?.show ?? "";
  const allocs: string[] = Array.isArray(p?.allocs) ? p.allocs : [];
  const targetJob: string = p?.targetJob ?? "";
  const minCores: number = Number(p?.minCores ?? 1);
  const maxCores: number = Number(p?.maxCores ?? 32);
  const minMemoryKb: number = Number(p?.minMemoryKb ?? 0);
  const limit: number = Math.max(1, Number(p?.limit ?? 10));
  const cutoffSeconds: number = Number(p?.cutoffSeconds ?? 72000);
  const requireService: string = (p?.requireService ?? "").trim();
  const includeGroups: string[] = Array.isArray(p?.includeGroups) ? p.includeGroups : [];
  const excludeRegex: string = (p?.excludeRegex ?? "").trim();

  if (!show) return NextResponse.json({ error: "A show is required" }, { status: 400 });

  const procsData = await gatewayJson(
    "/host.ProcInterface/GetProcs",
    JSON.stringify({ r: { shows: [show], allocs } }),
  );
  if (procsData === null) {
    return NextResponse.json({ error: "Failed to list procs" }, { status: 500 });
  }
  const procs: any[] = procsData?.procs?.procs ?? [];

  let excludeRe: RegExp | null = null;
  if (excludeRegex) {
    // Cap the pattern length before compiling user input: a bounded pattern
    // keeps the worst-case backtracking small and avoids a Regular Expression Denial of Service (ReDoS) vector.
    if (excludeRegex.length > 100) {
      return NextResponse.json({ error: "excludeRegex is too long (max 100 characters)" }, { status: 400 });
    }
    try {
      excludeRe = new RegExp(excludeRegex);
    } catch {
      excludeRe = null;
    }
  }

  // Group the surviving procs by host.
  const byHost = new Map<string, any[]>();
  for (const proc of procs) {
    if (proc.showName !== show) continue;
    if (proc.jobName === targetJob) continue;
    if (proc.redirectTarget) continue;
    if (excludeRe && excludeRe.test(proc.jobName)) continue;
    if (requireService && !(proc.services ?? []).includes(requireService)) continue;
    if (includeGroups.length && !includeGroups.includes(proc.groupName)) continue;
    const hostName = String(proc.name ?? "").split("/")[0];
    if (!hostName) continue;
    const arr = byHost.get(hostName) ?? [];
    arr.push(proc);
    byHost.set(hostName, arr);
  }

  const now = NOW();
  const results: any[] = [];
  for (const [hostName, hostProcs] of Array.from(byHost.entries())) {
    if (results.length >= limit) break;

    const hostData = await gatewayJson(
      "/host.HostInterface/FindHost",
      JSON.stringify({ name: hostName }),
    );
    const host = hostData?.host;
    if (!host) continue;

    const idleCores = Number(host.idleCores ?? 0);
    const idleMemory = Number(host.idleMemory ?? 0); // KB
    let cores = idleCores;
    let memKb = idleMemory;
    let timeSec = 0;
    for (const proc of hostProcs) {
      cores += Number(proc.reservedCores ?? 0);
      memKb += Number(proc.reservedMemory ?? 0);
      // Missing dispatchTime falls back to 0, reading as a long runtime so the
      // host is excluded by the cutoff (CueGUI parity).
      timeSec += now - Number(proc.dispatchTime ?? 0);
    }

    if (!(cores >= minCores && cores <= maxCores && memKb >= minMemoryKb && timeSec < cutoffSeconds)) {
      continue;
    }

    // Job Cores / Waiting Frames columns reflect a single representative job on
    // the host (the first proc's), not a sum across every job - matching
    // CueGUI's Redirect, so they are intentionally not aggregated here.
    let jobCores = 0;
    let waiting = 0;
    const firstJobName = hostProcs[0]?.jobName;
    if (firstJobName) {
      const jobData = await gatewayJson(
        "/job.JobInterface/GetJobs",
        JSON.stringify({ r: { jobs: [firstJobName], include_finished: true } }),
      );
      const job = jobData?.jobs?.jobs?.[0];
      if (job) {
        jobCores = Number(job.jobStats?.reservedCores ?? 0);
        waiting = Number(job.jobStats?.waitingFrames ?? 0);
      }
    }

    results.push({
      name: hostName,
      host, // full Host object, needed by RedirectToJob
      alloc: host.allocName ?? "",
      cores,
      memoryKb: memKb,
      timeSeconds: timeSec,
      jobCores,
      waitingFrames: waiting,
      procs: hostProcs.map((proc) => ({
        id: proc.id,
        name: proc.name,
        jobName: proc.jobName,
        groupName: proc.groupName ?? "",
        services: proc.services ?? [],
        reservedCores: Number(proc.reservedCores ?? 0),
        reservedMemoryKb: Number(proc.reservedMemory ?? 0),
        runtimeSeconds: now - Number(proc.dispatchTime ?? now),
        showName: proc.showName ?? "",
      })),
    });
  }

  return NextResponse.json({ data: results }, { status: 200 });
}
