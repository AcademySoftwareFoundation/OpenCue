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

// Server-side data gathering for the Stuck Frames page. CueGUI's
// StuckFramePlugin walks every show's procs; we approximate by listing the
// unfinished jobs (GetJobs) and, per job, fetching its RUNNING frames
// (GetFrames, FrameState 2) and its layers (GetLayers, for the per-service
// average frame time). Each frame is stamped with its job, service and the
// layer's average frame time so the client can apply the full CueGUI
// stuck-detection predicate (LLU / % stuck / avg-completion / runtime) live
// against the user's per-service filter thresholds.
//
// RPCs: /job.JobInterface/GetJobs, /job.JobInterface/GetFrames,
//       /job.JobInterface/GetLayers.

const RUNNING_STATE = 2; // FrameState.RUNNING (proto/src/job.proto)
const MAX_FRAMES_PER_JOB = 1000;
// Cap the per-job GetFrames/GetLayers fan-out. Without a bound, a farm with
// thousands of unfinished jobs would fire that many concurrent gateway calls
// on every 30s poll; this keeps at most N jobs in flight at a time.
const MAX_CONCURRENT_JOBS = 16;

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

// Map over items with a fixed-size worker pool, preserving input order. Plain
// promises (no extra dependency) so the route stays self-contained.
async function mapWithConcurrency<T, R>(
  items: T[],
  limit: number,
  fn: (item: T, index: number) => Promise<R>,
): Promise<R[]> {
  const results: R[] = new Array(items.length);
  let cursor = 0;
  async function worker() {
    while (true) {
      const index = cursor++;
      if (index >= items.length) return;
      results[index] = await fn(items[index], index);
    }
  }
  const workerCount = Math.min(limit, items.length);
  await Promise.all(Array.from({ length: workerCount }, () => worker()));
  return results;
}

// Safety bound on pagination so a malformed/never-shrinking response can't spin
// forever: MAX_FRAME_PAGES * MAX_FRAMES_PER_JOB frames per job.
const MAX_FRAME_PAGES = 50;

// Fetch every RUNNING frame for a job, paging through GetFrames until a short
// page arrives. A single page caps at MAX_FRAMES_PER_JOB, so a job with more
// running frames than that would otherwise be silently truncated.
async function getRunningFrames(job: any): Promise<any[]> {
  const all: any[] = [];
  for (let page = 1; page <= MAX_FRAME_PAGES; page++) {
    const framesData = await gatewayJson(
      "/job.JobInterface/GetFrames",
      JSON.stringify({
        job: { id: job.id, name: job.name },
        req: {
          include_finished: false,
          page,
          limit: MAX_FRAMES_PER_JOB,
          states: { frame_states: [RUNNING_STATE] },
        },
      }),
    );
    const batch: any[] = Array.isArray(framesData?.frames?.frames) ? framesData.frames.frames : [];
    all.push(...batch);
    // A short (or empty/failed) page means we've reached the end.
    if (batch.length < MAX_FRAMES_PER_JOB) break;
  }
  return all;
}

export async function POST(_request: NextRequest) {
  try {
    const jobsData = await gatewayJson(
      "/job.JobInterface/GetJobs",
      JSON.stringify({ r: { include_finished: false } }),
    );
    if (jobsData === null) {
      return NextResponse.json({ error: "Failed to list jobs" }, { status: 500 });
    }
    const jobs: any[] = Array.isArray(jobsData?.jobs?.jobs) ? jobsData.jobs.jobs : [];

    const perJob = await mapWithConcurrency(
      jobs,
      MAX_CONCURRENT_JOBS,
      async (job) => {
        const [frames, layersData] = await Promise.all([
          getRunningFrames(job),
          gatewayJson(
            "/job.JobInterface/GetLayers",
            JSON.stringify({ job: { id: job.id, name: job.name } }),
          ),
        ]);

        const layers: any[] = Array.isArray(layersData?.layers?.layers) ? layersData.layers.layers : [];
        // layerName -> details for attaching to each frame (service + average
        // frame time for detection; id + minCores for the Core Up action).
        const layerInfo = new Map<
          string,
          { id: string; service: string; avgFrameSec: number; minCores: number }
        >();
        for (const layer of layers) {
          layerInfo.set(layer.name, {
            id: layer.id ?? "",
            service: Array.isArray(layer.services) && layer.services.length ? layer.services[0] : "",
            avgFrameSec: Number(layer.layerStats?.avgFrameSec ?? 0),
            minCores: Number(layer.minCores ?? 0),
          });
        }

        return frames
          .filter((f) => f.state === "RUNNING")
          .map((f) => {
            const info = layerInfo.get(f.layerName);
            return {
              ...f,
              jobId: job.id,
              jobName: job.name,
              jobLogDir: job.logDir ?? "",
              jobHasComment: !!job.hasComment,
              service: info?.service ?? "",
              avgFrameSec: info?.avgFrameSec ?? 0,
              layerId: info?.id ?? "",
              layerMinCores: info?.minCores ?? 0,
            };
          });
      },
    );

    return NextResponse.json({ data: perJob.flat() }, { status: 200 });
  } catch (error) {
    return NextResponse.json({ error: (error as Error).message }, { status: 500 });
  }
}
