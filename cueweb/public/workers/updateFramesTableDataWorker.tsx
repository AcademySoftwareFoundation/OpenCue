import { Job } from "@/app/jobs/columns";
import { getFramesForJob } from "@/app/utils/get_utils";

export interface WorkerMessage {
  job: Job;
}

export interface WorkerResponse {
  frames?: any[];   // Array of frames for the job
  error?: string;   // Error message in case of failure
}

// Web worker to update frames if their attributes have changed
self.onmessage = async (e: MessageEvent<WorkerMessage>) => {
  try {
    const { job } = e.data;
    const updatedFrames = await getFramesForJob(job);

    // If no frames are found, handle it gracefully without throwing an error
    if (!updatedFrames || updatedFrames.length === 0) {
      self.postMessage({ updatedFrames: [] } as WorkerResponse);
      return;
    }

    // Post the updated frames data back to the main thread
    self.postMessage({ updatedFrames } as WorkerResponse);
  } catch (error) {
    // Post the error message back to the main thread
    const errorMessage = error instanceof Error ? error.message : "Unhandled error in updateFramesTableDataWorker";
    self.postMessage({ error: errorMessage } as WorkerResponse);
  }
};
