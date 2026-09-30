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

import { Job } from "@/app/jobs/columns";

// Interface to define the structure of messages expected by the worker
export interface WorkerMessage {
  allJobs: Job[];
  query: string;
}

// Event listener for incoming messages to the worker
self.onmessage = function (e: MessageEvent<WorkerMessage>) {
  try {
    const { allJobs, query } = e.data;

    // Filter jobs down based on the current query (case insensitive)
    const filteredJobs = allJobs.filter((job: Job) => job.name.toLowerCase().includes(query.toLowerCase()));

    // Post the filtered jobs back to the main thread
    self.postMessage(filteredJobs);
  } catch (e) {
    // Catch errors based on type
    if (typeof e === "string") {
      self.postMessage({ error: e });
    } else if (e instanceof Error) {
      self.postMessage({ error: e.message });
    } else {
      self.postMessage({ error: "unhandled error in searchFilterWorker" });
    }
  }
};
