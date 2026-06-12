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

import path from "path";
import { Job } from "../jobs/columns";
import { Layer } from "../layers/layer-columns";
import { accessGetApi } from "./api_utils";
import { Frame } from "../frames/frame-columns";

/********************************************************************/
// Utility functions for getting objects like jobs, layers, and frames
/********************************************************************/

// Mirrors the comment.Comment proto message at proto/src/comment.proto.
export type JobComment = {
    id: string;
    timestamp: number;
    user: string;
    subject: string;
    message: string;
};

// Mirrors the job.Group proto message at proto/src/job.proto.
export type Group = {
    id: string;
    name: string;
    department: string;
    defaultJobPriority: number;
    defaultJobMinCores: number;
    defaultJobMaxCores: number;
    minCores: number;
    maxCores: number;
    level: number;
    parentId: string;
    groupStats?: GroupStats;
};

// Mirrors the job.GroupStats proto message at proto/src/job.proto.
export type GroupStats = {
    runningFrames: number;
    deadFrames: number;
    dependFrames: number;
    waitingFrames: number;
    pendingJobs: number;
    reservedCores: number;
    reservedGpus: number;
};

export type Depend = {
    id: string;
    type: string | number;
    target: string | number;
    anyFrame: boolean;
    active: boolean;
    dependErJob: string;
    dependErLayer: string;
    dependErFrame: string;
    dependOnJob: string;
    dependOnLayer: string;
    dependOnFrame: string;
};

// Minimal Host shape - matches the host.Host proto fields the dashboard
// and the Monitor Hosts / host detail pages care about.
export type Host = {
    id: string;
    name: string;
    state: string;        // HardwareState: UP / DOWN / REBOOTING / REBOOT_WHEN_IDLE / REPAIR
    lockState: string;    // OPEN / LOCKED / NIMBY_LOCKED
    nimbyEnabled: boolean;
    cores: number;
    idleCores: number;
    memory: string;       // KB, as string from the gateway
    idleMemory: string;   // KB, as string
    totalMemory: string;  // KB, as string
    freeMcp: string;      // KB, as string
    bootTime: number;
    pingTime: number;
    // Extra fields surfaced on the host detail page. Optional so the
    // dashboard/Monitor Hosts callers that don't request them still typecheck.
    allocName?: string;
    os?: string;
    load?: number;
    tags?: string[];
    threadMode?: string;  // ThreadMode: AUTO / ALL / VARIABLE
    gpus?: number;
    idleGpus?: number;
    hasComment?: boolean;
};

// Minimal Proc shape - the host.Proc proto fields the host detail page's
// running-procs table needs. Memory values arrive from the gateway as
// KB-in-string, mirroring the Host memory fields.
export type Proc = {
    id: string;
    name: string;
    showName: string;
    jobName: string;
    frameName: string;
    groupName: string;
    pingTime: number;
    bookedTime: number;
    dispatchTime: number;
    reservedMemory: string;   // KB, as string
    usedMemory: string;       // KB, as string
    reservedCores: number;
    services: string[];
    logPath: string;
    unbooked: boolean;
};

// Mirrors the show.Show proto message at proto/src/show.proto.
export type Show = {
    id: string;
    name: string;
    active: boolean;
    showStats?: {
        runningFrames: number;
        pendingFrames: number;
        deadFrames: number;
        pendingJobs: number;
    };
};

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

// Fetch a single job by its UUID. Typed wrapper around getPendingJob for caller ergonomics.
export async function getJob(jobId: string): Promise<Job | null> {
    return getPendingJob(JSON.stringify({ id: jobId }));
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

// Fetch jobs for a specific user. include_finished defaults to false to
// match the CueGUI Monitor Jobs default; pass `true` from callers that
// surface the "Load Finished" checkbox.
export async function getJobsForUser(user: string, includeFinished: boolean = false): Promise<Job[]> {
    const body = { r: { include_finished: includeFinished, users: [`${user}`] } };
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
 * @param includeFinished - When false, omits jobs whose state is FINISHED
 *   so the "Load Finished" toggle in the Monitor Jobs UI can gate them
 *   out. Defaults to true for backward compatibility with older callers.
 * @returns A promise that resolves to the list of jobs matching the regex pattern.
 */
export async function getJobsForRegex(regex: string, includeFinished: boolean = true): Promise<Job[]> {
    const body = { r: { include_finished: includeFinished, regex: [`${regex}`] } };
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

// Fetch all dependencies for a given job. Routes through the validated
// proxy at /api/job/action/getdepends (camelCase fields, double-
// nested response). Tolerates both nested and flat shapes so a gateway
// marshaller change can't silently break the consumer.
export async function getDependsForJob(job: Job): Promise<Depend[]> {
    const ENDPOINT = "/api/job/action/getdepends";
    const body = JSON.stringify({ job: { id: job.id, name: job.name } });
    const data = await accessGetApi(ENDPOINT, body);
    if (!data) return [];
    const seq: any = data?.depends?.depends ?? data?.depends ?? data;
    return Array.isArray(seq) ? (seq as Depend[]) : [];
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

// Fetch every host known to Cuebot. Optionally accepts a host-search filter (HostSearchCriteria).
// Returns an array (possibly empty) on success; throws on a failed request so
// callers can tell a real failure apart from an empty registry.
export async function getHosts(body: string = JSON.stringify({ r: {} })): Promise<Host[]> {
    const ENDPOINT = "/api/host/gethosts";
    const response = await accessGetApi(ENDPOINT, body);
    if (!Array.isArray(response)) {
        throw new Error("Failed to load hosts from Cuebot.");
    }
    return response;
}

// Resolve a single host by its exact name (FindHost). Returns null when no
// host matches so the detail page can render a "host not found" state.
export async function findHostByName(name: string): Promise<Host | null> {
    const ENDPOINT = "/api/host/findhost";
    const response = await accessGetApi(ENDPOINT, JSON.stringify({ name }));
    return response ?? null;
}

// Fetch the procs (booked frames) running on a host.
export async function getHostProcs(host: Host): Promise<Proc[]> {
    const ENDPOINT = "/api/host/getprocs";
    const response = await accessGetApi(ENDPOINT, JSON.stringify({ host }));
    return Array.isArray(response) ? response : [];
}

// Fetch the comments attached to a host (same comment.Comment shape as jobs).
export async function getHostComments(host: Host): Promise<JobComment[]> {
    const ENDPOINT = "/api/host/getcomments";
    const response = await accessGetApi(ENDPOINT, JSON.stringify({ host }));
    return Array.isArray(response) ? response : [];
}

// Fetch every show known to Cuebot.
export async function getShows(): Promise<Show[]> {
    const ENDPOINT = "/api/show/getshows";
    const response = await accessGetApi(ENDPOINT, JSON.stringify({}));
    return Array.isArray(response) ? response : [];
}

// Fetch all comments for a given job
export async function getJobComments(job: Job): Promise<JobComment[]> {
    const ENDPOINT = "/api/job/getcomments";
    const body = JSON.stringify({ job: { id: job.id, name: job.name } });
    const response = await accessGetApi(ENDPOINT, body);
    return Array.isArray(response) ? response : [];
}

// Look up a single show by its name. Returns null if no show matches.
export async function findShowByName(showName: string): Promise<Show | null> {
    const ENDPOINT = "/api/show/findshow";
    const body = JSON.stringify({ name: showName });
    const response = await accessGetApi(ENDPOINT, body);
    return response ?? null;
}

// Fetch the root group's subgroups for a show
export async function getShowGroups(showId: string): Promise<Group[]> {
    const ENDPOINT = "/api/show/getgroups";
    const body = JSON.stringify({ show: { id: showId } });
    const response = await accessGetApi(ENDPOINT, body);
    return Array.isArray(response) ? response : [];
}

// Fetch the direct jobs in a group
export async function getGroupJobs(groupId: string): Promise<Job[]> {
    const ENDPOINT = "/api/group/getjobs";
    const body = JSON.stringify({ group: { id: groupId } });
    const response = await accessGetApi(ENDPOINT, body);
    return Array.isArray(response) ? response : [];
}

// Fetch the depend.DependSeq of every job currently blocked on the
// supplied job. The Cuebot REST gateway emits camelCase field names
// (proto `depend_er_job` -> JSON `dependErJob`) and double-nests the
// list as `{depends: {depends: [...]}}`. We accept both camelCase and
// snake_case as a belt-and-braces fallback against gateway-side
// marshaller config changes. Returns the list of dependent job names
// so the caller can build a parent -> children adjacency map without
// re-parsing.
export async function getWhatDependsOnThisJobNames(job: Job): Promise<string[]> {
    const ENDPOINT = "/api/job/action/getwhatdependsonthis";
    const body = JSON.stringify({ job: { id: job.id, name: job.name } });
    const data = await accessGetApi(ENDPOINT, body);
    if (!data) return [];
    const seq: any[] = data?.depends?.depends ?? data?.depends ?? [];
    if (!Array.isArray(seq)) return [];
    // Mirrors CueGUI's filter: only active depends contribute children.
    // A satisfied / dropped depend should NOT keep the dependent job
    // nested under the parent.
    const names = new Set<string>();
    for (const d of seq) {
        if (d?.active === false) continue;
        const name: string | undefined = d?.dependErJob ?? d?.depend_er_job;
        if (typeof name === "string" && name && name !== job.name) names.add(name);
    }
    return Array.from(names);
}
