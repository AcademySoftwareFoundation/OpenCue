import { Job } from "@/app/jobs/columns";
import { getJobs } from "@/app/utils/get_utils";

export interface WorkerMessage {
  jobs: Job[];
}

export interface WorkerResponse {
  updatedJobs?: Job[];
  error?: string;
}

// Web worker to update jobs if their attributes have changed
self.onmessage = async (e: MessageEvent<WorkerMessage>) => {
  try {
    const { jobs } = e.data;

    if (jobs.length === 0) {
      self.postMessage({ updatedJobs: [] } as WorkerResponse);
      return;
    }

    const updatedJobs: Job[] = [];

    // Fetch updated data for each job concurrently, limiting concurrency to avoid overwhelming the gRPC API
    await Promise.all(
      jobs.map(async (job) => {
        const body = JSON.stringify({ r: { include_finished: true, ids: [job.id] } });
        const newJobData = await getJobs(body);
        
        if (newJobData.length !== 0) {
          updatedJobs.push(newJobData[0]);
        }
      })
    );

    // Post the updated job data back to the main thread
    self.postMessage({ updatedJobs } as WorkerResponse);
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : "Unhandled error in updateJobsTableDataWorker";
    self.postMessage({ error: errorMessage } as WorkerResponse);
  }
};