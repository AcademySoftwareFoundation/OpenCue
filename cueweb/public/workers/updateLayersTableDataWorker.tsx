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
