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

    if (!Array.isArray(jobs) || !jobs.every(isValidJob)) {
      throw new Error("Invalid job data received by worker");
    }

    const ids = jobs.map(job => job.id);
    const updatedJobs: Job[] = [];

    // Fetch updated data for each job concurrently, limiting concurrency to avoid overwhelming the gRPC API
    await Promise.all(
      ids.map(async (id) => {
        const body = JSON.stringify({ r: { include_finished: true, ids: [id] } });
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

// Function to validate the structure of a Job object
function isValidJob(job: any): job is Job {
  return typeof job === 'object' && job !== null && typeof job.id === 'string' && job.id.trim().length > 0;
}
