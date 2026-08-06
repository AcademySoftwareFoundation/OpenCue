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

import type { Job } from "@/app/jobs/columns";
import { getJobStateDotColor, getState } from "@/app/utils/job_state";

const job = (
  overrides: Omit<Partial<Job>, "jobStats"> & { jobStats?: Partial<Job["jobStats"]> },
): Job =>
  ({
    state: "RUNNING",
    isPaused: false,
    ...overrides,
    jobStats: {
      totalFrames: 10,
      succeededFrames: 0,
      runningFrames: 1,
      waitingFrames: 0,
      dependFrames: 0,
      pendingFrames: 0,
      deadFrames: 0,
      ...overrides.jobStats,
    },
  }) as Job;

describe("getState", () => {
  it("reports Finished, Paused, Failing, Dependency, and In Progress", () => {
    expect(getState(job({ state: "FINISHED" }))).toBe("Finished");
    expect(getState(job({ isPaused: true }))).toBe("Paused");
    expect(getState(job({ jobStats: { deadFrames: 1 } }))).toBe("Failing");
    expect(
      getState(job({ jobStats: { dependFrames: 4, pendingFrames: 4, runningFrames: 0 } })),
    ).toBe("Dependency");
    expect(getState(job({ jobStats: { runningFrames: 2 } }))).toBe("In Progress");
  });
});

describe("getJobStateDotColor", () => {
  it("is green for a finished job", () => {
    expect(getJobStateDotColor(job({ state: "FINISHED" }))).toBe("bg-green-500");
  });

  it("is blue for a paused job", () => {
    expect(getJobStateDotColor(job({ isPaused: true }))).toBe("bg-blue-500");
  });

  it("is red for a failing job (dead frames)", () => {
    expect(getJobStateDotColor(job({ jobStats: { deadFrames: 3 } }))).toBe("bg-red-500");
  });

  it("is purple for a dependency job", () => {
    expect(
      getJobStateDotColor(
        job({ jobStats: { dependFrames: 4, pendingFrames: 4, runningFrames: 0 } }),
      ),
    ).toBe("bg-purple-500");
  });

  it("is yellow for an in-progress job", () => {
    expect(getJobStateDotColor(job({ jobStats: { runningFrames: 2 } }))).toBe("bg-yellow-500");
  });

  it("respects paused precedence over dead frames (blue, matching getState)", () => {
    // A paused job that also has dead frames is reported as Paused, not Failing.
    expect(getJobStateDotColor(job({ isPaused: true, jobStats: { deadFrames: 5 } }))).toBe(
      "bg-blue-500",
    );
  });
});
