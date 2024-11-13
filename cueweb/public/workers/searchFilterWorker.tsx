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
