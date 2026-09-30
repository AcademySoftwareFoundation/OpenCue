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
import { getJobProgressSegments, getJobProgressTooltipRows } from "@/app/utils/job_progress_utils";

const job = (stats: Partial<Job["jobStats"]>): Job =>
  ({
    jobStats: {
      totalFrames: 10,
      succeededFrames: 4,
      runningFrames: 2,
      waitingFrames: 1,
      dependFrames: 2,
      deadFrames: 1,
      ...stats,
    },
  }) as Job;

describe("job_progress_utils", () => {
  it("returns progress segment percentages", () => {
    expect(getJobProgressSegments(job({})).map((segment) => segment.percentage)).toEqual([
      "40%",
      "20%",
      "10%",
      "20%",
      "10%",
    ]);
  });

  it("returns tooltip rows with counts and rounded percentages", () => {
    expect(getJobProgressTooltipRows(job({ totalFrames: 12, succeededFrames: 5 }))[0]).toEqual({
      label: "Succeeded",
      count: 5,
      percentage: "41.7%",
    });
  });

  it("uses zero percentages when total frame count is zero", () => {
    expect(getJobProgressTooltipRows(job({ totalFrames: 0, succeededFrames: 5 }))[0].percentage).toBe("0.0%");
    expect(getJobProgressSegments(job({ totalFrames: 0, succeededFrames: 5 }))[0].percentage).toBe("0%");
  });
});
