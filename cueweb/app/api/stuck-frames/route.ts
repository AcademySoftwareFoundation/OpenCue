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

// Server-side aggregation for the Stuck Frames page. There is no single RPC
// that returns every running frame, so we list the unfinished jobs
// (GetJobs) and fan out a GetFrames call per job filtered to RUNNING
// (FrameState 2), then flatten. Doing the fan-out here keeps the browser to a
// single request and avoids leaking the N+1 to the client. The page applies
// the running-time threshold locally so the slider stays instant.
//
// RPCs: /job.JobInterface/GetJobs, /job.JobInterface/GetFrames.

const RUNNING_STATE = 2; // FrameState.RUNNING (proto/src/job.proto)
const MAX_FRAMES_PER_JOB = 1000;

export async function POST(_request: NextRequest) {
  try {
    // 1. All unfinished jobs.
    const jobsResp = await fetchObjectFromRestGateway(
      "/job.JobInterface/GetJobs",
      "POST",
      JSON.stringify({ r: { include_finished: false } }),
    );
    const jobsJson = await jobsResp.json();
    if (jobsJson?.error) {
      return NextResponse.json({ error: jobsJson.error }, { status: 500 });
    }
    const jobs: any[] = jobsJson?.data?.jobs?.jobs ?? [];

    // 2. Running frames per job, in parallel. A single job's failure drops to
    //    an empty list rather than failing the whole page.
    const perJob = await Promise.all(
      jobs.map(async (job) => {
        const body = JSON.stringify({
          job: { id: job.id, name: job.name },
          req: {
            include_finished: false,
            page: 1,
            limit: MAX_FRAMES_PER_JOB,
            states: { frame_states: [RUNNING_STATE] },
          },
        });
        try {
          const framesResp = await fetchObjectFromRestGateway(
            "/job.JobInterface/GetFrames",
            "POST",
            body,
          );
          const framesJson = await framesResp.json();
          if (framesJson?.error) return [];
          const frames: any[] = framesJson?.data?.frames?.frames ?? [];
          // Defensive: keep only RUNNING even if the state filter was ignored,
          // and stamp the parent job so the table can show / act on it.
          return frames
            .filter((f) => f.state === "RUNNING")
            .map((f) => ({ ...f, jobId: job.id, jobName: job.name }));
        } catch {
          return [];
        }
      }),
    );

    return NextResponse.json({ data: perJob.flat() }, { status: 200 });
  } catch (error) {
    return NextResponse.json({ error: (error as Error).message }, { status: 500 });
  }
}
