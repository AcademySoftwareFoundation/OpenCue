import path from "path";
import { Job } from "../jobs/columns";
import { Layer } from "../layers/layer-columns";
import { accessGetApi } from "./api_utils";
import { Frame } from "../frames/frame-columns";

/********************************************************************/
// Utility functions for getting objects like jobs, layers, and frames
/********************************************************************/

// Fetch a single frame based on the request body
export async function getFrame(body: string): Promise<Frame | null> {
    const ENDPOINT = "/api/frame/getframe";
    const response = await accessGetApi(ENDPOINT, body);
    return response;
}

// Fetch multiple frames based on the request body
export async function getFrames(body: string): Promise<Frame[]> {
    const ENDPOINT = "/api/job/getframes";
    const response = await accessGetApi(ENDPOINT, body);
    return response ? response : [];
}

// Fetch a pending job based on the request body
export async function getPendingJob(body: string): Promise<Job | null> {
    const ENDPOINT = "/api/job/getjob";
    const response = await accessGetApi(ENDPOINT, body);
    return response;
}

// Fetch all jobs based on the request body
export async function getJobs(body: string): Promise<Job[]> {
    const ENDPOINT = "/api/job/getjobs";
    const response = await accessGetApi(ENDPOINT, body);
    return response ? response : [];
}

// Fetch all layers based on the request body
export async function getLayers(body: string): Promise<Layer[]> {
    const ENDPOINT = "/api/job/getlayers";
    const response = await accessGetApi(ENDPOINT, body);
    return response ? response : [];
}

// Fetch jobs for a specific user, including finished jobs
export async function getJobsForUser(user: string): Promise<Job[]> {
    const body = { r: { include_finished: false, users: [`${user}`] } };
    return await getJobs(JSON.stringify(body));
}

/*
 * Fetches all jobs given the show name and shot name.
 * @param show - The show's name to get jobs from.
 * @param shot - The shot's name to get the jobs from.
 * @returns A promise that resolves to the list of all jobs from the show and shot.
 */
export async function getJobsForShowShot(show: string, shot: string): Promise<Job[]> {
    const body = { r: { include_finished: true, shows: [`${show}`], shots: [`${shot}`] } };
    return getJobs(JSON.stringify(body));
}

/*
 * Fetches jobs that match a given regex pattern.
 * @param regex - The regex pattern to search for in job names.
 * @returns A promise that resolves to the list of jobs matching the regex pattern.
 */
export async function getJobsForRegex(regex: string): Promise<Job[]> {
    const body = { r: { include_finished: true, regex: [`${regex}`] } };
    return getJobs(JSON.stringify(body));
}

// Fetch all layers for a given job
export async function getLayersForJob(job: Job): Promise<Layer[]> {
    const body = { job: { id: `${job.id}` } };
    return getLayers(JSON.stringify(body));
}

// Fetch all frames for a given job
export async function getFramesForJob(job: Job): Promise<Frame[]> {
    const body = {
        job: { id: `${job.id}`, name: `${job.name}` },
        req: { include_finished: true, page: 1, limit: 500 },
    };
    return getFrames(JSON.stringify(body));
}

// Get the job that a layer belongs to using the layer's parentId
export async function getJobForLayer(layer: Layer): Promise<Job | null> {
    const body = JSON.stringify({ r: { include_finished: true, ids: [`${layer.parentId}`] } });
    const jobResponse = await getJobs(body);

    return jobResponse.length ? jobResponse[0] : null;
}

// Get the log directory path for a given frame within a job
export const getFrameLogDir = (job: Job, frame: Frame): string => {
    return path.join(job.logDir, `${job.name}.${frame.name}.rqlog`);
};
