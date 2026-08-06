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
import { getLayersForJob } from "@/app/utils/get_utils";

export interface WorkerMessage {
  job: Job;
}

export interface WorkerResponse {
  updatedLayers?: any[];
  error?: string;
}

// Web worker to update layers if their attributes have changed
self.onmessage = async (e: MessageEvent<WorkerMessage>) => {
  try {
    const { job } = e.data;

    // Fetch updated layers for the job
    const updatedLayers = await getLayersForJob(job);

    // If no layers are found, handle the case with a proper error
    if (updatedLayers.length === 0) {
      throw new Error("No layers found for job in updateLayersTableDataWorker.tsx");
    }

    // Post updated layers back to the main thread
    self.postMessage({ updatedLayers } as WorkerResponse);
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : "Unhandled error in updateLayersTableDataWorker";
    
    // Send error back to the main thread
    self.postMessage({ error: errorMessage } as WorkerResponse);
  }
};
