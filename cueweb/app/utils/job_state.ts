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

// Job display state. In a pure module (re-exported from columns.tsx) so rows can
// reuse it and unit-test it without importing the JSX-heavy columns module.
export const getState = (job: Job) => {
  if (job?.state === "FINISHED") {
    return "Finished";
  }
  if (job?.isPaused) {
    return "Paused";
  }
  if (job?.jobStats.deadFrames > 0) {
    return "Failing";
  }
  if (
    job?.jobStats.dependFrames &&
    job?.jobStats.dependFrames === job?.jobStats.pendingFrames &&
    job?.jobStats.runningFrames === 0
  ) {
    return "Dependency";
  }
  return "In Progress";
};

const STATE_DOT_COLORS: Record<string, string> = {
  Finished: "bg-green-500",
  Paused: "bg-blue-500",
  Failing: "bg-red-500",
  Dependency: "bg-purple-500",
  "In Progress": "bg-yellow-500",
};

export const getJobStateDotColor = (job: Job): string => STATE_DOT_COLORS[getState(job)] ?? "bg-gray-400";
