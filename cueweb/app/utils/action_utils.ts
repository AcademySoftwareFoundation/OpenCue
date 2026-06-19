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
import { Row } from "@tanstack/react-table";
import * as React from "react";
import { Frame } from "../frames/frame-columns";
import { Layer } from "../layers/layer-columns";
import { accessActionApi, accessGetApi } from "./api_utils";
import { getFrameLogDir, getJobForLayer, Host, JobComment, Limit, Service, Show, Subscription } from "./get_utils";
import {
  OPEN_DELETE_SUBSCRIPTION_EVENT,
  OPEN_EDIT_SUBSCRIPTION_BURST_EVENT,
  OPEN_EDIT_SUBSCRIPTION_SIZE_EVENT,
} from "@/components/ui/subscription-action-events";
import { handleError, toastSuccess, toastWarning } from "./notify_utils";

/**************************************/
// Helper function for API calls
/**************************************/

// Returns true when the action succeeded, false otherwise. Errors are still
// surfaced via handleError (a toast); the boolean lets callers gate optimistic
// UI updates on success so they don't briefly show a state the backend
// rejected. Existing callers that ignore the return value are unaffected.
export async function performAction(endpoint: string, bodyAr: string[], successMessage: string): Promise<boolean> {
  if (bodyAr.length === 0) return false;

  try {
    const result = await accessActionApi(endpoint, bodyAr);
    if (result?.success) {
      toastSuccess(successMessage);
      return true;
    } else {
      throw new Error(result.error);
    }
  } catch (error) {
    handleError(error, `Error performing action for: ${endpoint}`);
    return false;
  }
}

/**************************************/
// Facility default services (CueGUI ServiceDialog parity)
/**************************************/

// These call accessActionApi directly (no per-call success toast) so the
// Facility Service Defaults form can show a single toast after the call
// resolves. Errors are still surfaced as toasts by accessActionApi. Returns
// true on success so the form can gate its refresh on it.
export async function createService(data: Service): Promise<boolean> {
  const result = await accessActionApi("/api/service/create", JSON.stringify({ data }));
  return !!result?.success;
}

export async function updateService(service: Service): Promise<boolean> {
  const result = await accessActionApi("/api/service/update", JSON.stringify({ service }));
  return !!result?.success;
}

export async function deleteService(service: Service): Promise<boolean> {
  const result = await accessActionApi("/api/service/delete", JSON.stringify({ service }));
  return !!result?.success;
}

/**************************************/
// Kill Jobs, Layers, and Frames
/**************************************/

export async function killJobs(jobs: Job[], username: string, reason: string) {
  const endpoint = "/api/job/action/kill";
  const bodyAr = jobs.map(job => JSON.stringify({
    job,
    username,
    reason
  }));
  await performAction(endpoint, bodyAr, `Killed ${jobs.length} job(s)`);
}

export async function killLayers(layers: Layer[], username: string, reason: string) {
  const endpoint = "/api/layer/action/kill";
  const bodyAr = layers.map(layer => JSON.stringify({
    layer,
    username,
    reason
  }));
  await performAction(endpoint, bodyAr, `Killed ${layers.length} layer(s)`);
}

export async function killFrames(frames: Frame[], username: string, reason: string) {
  const endpoint = "/api/frame/action/kill";
  const bodyAr = frames.map(frame => JSON.stringify({
    frame,
    username,
    reason
  }));
  await performAction(endpoint, bodyAr, `Killed ${frames.length} frame(s)`);
}


/**************************************/
// Eat Jobs, Layers, and Frames
/**************************************/

export async function eatJobsDeadFrames(jobs: Job[]) {
  const endpoint = "/api/job/action/eatframes";
  const bodyAr = jobs.map(job => JSON.stringify({
    job,
    req: { states: { frame_states: [5] } } // Only eat dead frames
  }));
  await performAction(endpoint, bodyAr, `Ate ${jobs.length} job(s)`);
}

export async function eatLayersFrames(layers: Layer[]) {
  const endpoint = "/api/layer/action/eatframes";
  const bodyAr = layers.map(layer => JSON.stringify({
    layer
  }));
  await performAction(endpoint, bodyAr, `Ate ${layers.length} layer(s)`);
}

export async function eatFrames(frames: Frame[]) {
  const endpoint = "/api/frame/action/eat";
  const bodyAr = frames.map(frame => JSON.stringify({
    frame
  }));
  await performAction(endpoint, bodyAr, `Ate ${frames.length} frame(s)`);
}

  
/**************************************/
// Retry Jobs, Layers, and Frames
/**************************************/
export async function retryJobsDeadFrames(jobs: Job[]) {
  const endpoint = "/api/job/action/retryframes";
  const bodyAr = jobs.map(job => JSON.stringify({
    job,
    req: { states: { frame_states: [5] } } // Retry dead frames
  }));
  await performAction(endpoint, bodyAr, `Retried ${jobs.length} job(s)`);
}

export async function retryLayersFrames(layers: Layer[]) {
  const endpoint = "/api/layer/action/retryframes";
  const bodyAr = layers.map(layer => JSON.stringify({
    layer
  }));
  await performAction(endpoint, bodyAr, `Retried ${layers.length} layer(s)`);
}

export async function retryLayersDeadFrames(layers: Layer[]) {
  const endpoint = "/api/job/action/retryframes";
  const bodyAr = [];

  for (const layer of layers) {
    const job = await getJobForLayer(layer);
    if (job) {
      bodyAr.push(JSON.stringify({
        job,
        req: {
          layers: [layer.name],
          states: { frame_states: [5] }
        }
      }));
    }
  }

  if (bodyAr.length > 0) {
    await performAction(endpoint, bodyAr, `Retried ${bodyAr.length} layer(s)`);
  }
}

export async function retryFrames(frames: Frame[]) {
  const endpoint = "/api/frame/action/retry";
  const bodyAr = frames.map(frame => JSON.stringify({
    frame
  }));
  await performAction(endpoint, bodyAr, `Retried ${frames.length} frame(s)`);
}

/**************************************/
// Unbook
/**************************************/

// Unbook every proc a job currently holds (CueWeb #2288). Job-scoped MVP:
// the proc search criteria is just { jobs: [job.name] }. kill=true also kills
// the running frames. Allocation / amount / redirect scoping from CueGUI's
// UnbookDialog is intentionally deferred. Returns performAction's success
// boolean so the dialog can gate its table refresh on success.
export async function unbookJob(job: Job, kill: boolean): Promise<boolean> {
  const endpoint = "/api/proc/action/unbook";
  const body = JSON.stringify({ r: { jobs: [job.name] }, kill });
  return performAction(endpoint, [body], kill ? `Unbooked and killed procs on ${job.name}` : `Unbooked procs on ${job.name}`);
}

/**************************************/
// Job Comments
/**************************************/
export async function addJobComment(
  job: Job,
  username: string,
  subject: string,
  message: string,
) {
  const endpoint = "/api/job/action/addcomment";
  const body = JSON.stringify({
    job: { id: job.id, name: job.name },
    new_comment: {
      user: username,
      subject,
      message,
    },
  });
  await performAction(endpoint, [body], "Added comment");
}

export async function saveJobComment(comment: JobComment) {
  const endpoint = "/api/comment/action/save";
  const body = JSON.stringify({ comment });
  await performAction(endpoint, [body], "Saved comment");
}

export async function deleteJobComment(comment: JobComment) {
  const endpoint = "/api/comment/action/delete";
  const body = JSON.stringify({ comment });
  await performAction(endpoint, [body], "Deleted comment");
}

/**************************************/
// Pause/Unpause Jobs
/**************************************/
export async function pauseJobs(jobs: Job[]) {
  const endpoint = "/api/job/action/pause";
  const bodyAr = jobs.map(job => JSON.stringify({ job }));
  await performAction(endpoint, bodyAr, `Paused ${jobs.length} job(s)`);
}

export async function unpauseJobs(jobs: Job[]) {
  const endpoint = "/api/job/action/unpause";
  const bodyAr = jobs.map(job => JSON.stringify({ job }));
  await performAction(endpoint, bodyAr, `Unpaused ${jobs.length} job(s)`);
}

/**************************************/
// Reparent Groups and Jobs
/**************************************/

export async function reparentGroups(newParentId: string, groupIds: string[]) {
  const endpoint = "/api/group/action/reparentgroups";
  const body = JSON.stringify({
    group: { id: newParentId },
    groups: { groups: groupIds.map(id => ({ id })) },
  });
  return performAction(endpoint, [body], `Reparented ${groupIds.length} group(s)`);
}

export async function reparentJobs(newParentId: string, jobIds: string[]) {
  const endpoint = "/api/group/action/reparentjobs";
  const body = JSON.stringify({
    group: { id: newParentId },
    jobs: { jobs: jobIds.map(id => ({ id })) },
  });
  return performAction(endpoint, [body], `Reparented ${jobIds.length} job(s)`);
}

/**************************************/
// Lock/Unlock Hosts (CueCommander parity)
/**************************************/

// Lock the given hosts so they stop booking new frames. Batch-capable:
// each host is locked in parallel via performAction, mirroring pauseJobs.
export async function lockHosts(hosts: Host[]): Promise<boolean> {
  const endpoint = "/api/host/action/lock";
  const bodyAr = hosts.map(host => JSON.stringify({ host }));
  return performAction(endpoint, bodyAr, `Locked ${hosts.length} host(s)`);
}

// Unlock the given hosts, returning them to the booking pool. NIMBY-locked
// hosts cannot be unlocked this way (the gateway rejects them); the context
// menu disables Unlock for those so the request never reaches here.
export async function unlockHosts(hosts: Host[]): Promise<boolean> {
  const endpoint = "/api/host/action/unlock";
  const bodyAr = hosts.map(host => JSON.stringify({ host }));
  return performAction(endpoint, bodyAr, `Unlocked ${hosts.length} host(s)`);
}

/**************************************/
// Reboot Hosts (CueCommander parity)
/**************************************/

// Immediately reboot the given hosts. Cuebot flips each to REBOOTING and
// signals RQD; frames running on those hosts are killed. Batch-capable.
export async function rebootHosts(hosts: Host[]): Promise<boolean> {
  const endpoint = "/api/host/action/reboot";
  const bodyAr = hosts.map(host => JSON.stringify({ host }));
  return performAction(endpoint, bodyAr, `Rebooting ${hosts.length} host(s)`);
}

// Schedule a reboot for when the given hosts go idle (REBOOT_WHEN_IDLE).
// Nothing is killed - the reboot waits for running frames to finish.
export async function rebootHostsWhenIdle(hosts: Host[]): Promise<boolean> {
  const endpoint = "/api/host/action/rebootwhenidle";
  const bodyAr = hosts.map(host => JSON.stringify({ host }));
  return performAction(endpoint, bodyAr, `Scheduled reboot-when-idle for ${hosts.length} host(s)`);
}

/**************************************/
// Host Tags (CueCommander parity)
/**************************************/

// Add the given tags to every host. No-op when there are no tags to add.
export async function addHostTags(hosts: Host[], tags: string[]): Promise<boolean> {
  if (tags.length === 0) return false;
  const endpoint = "/api/host/action/addtags";
  const bodyAr = hosts.map(host => JSON.stringify({ host, tags }));
  return performAction(endpoint, bodyAr, `Added ${tags.length} tag(s) to ${hosts.length} host(s)`);
}

// Remove the given tags from every host. No-op when there are no tags to remove.
export async function removeHostTags(hosts: Host[], tags: string[]): Promise<boolean> {
  if (tags.length === 0) return false;
  const endpoint = "/api/host/action/removetags";
  const bodyAr = hosts.map(host => JSON.stringify({ host, tags }));
  return performAction(endpoint, bodyAr, `Removed ${tags.length} tag(s) from ${hosts.length} host(s)`);
}

/**************************************/
// Priority / retries / auto-eat / depends (CueGUI parity)
/**************************************/

export async function setJobPriority(job: Job, priority: number) {
  const endpoint = "/api/job/action/setpriority";
  await performAction(endpoint, [JSON.stringify({ job, val: priority })], `Set priority ${priority} on ${job.name}`);
}

// Set a job's min and max cores in one user action (CueWeb #2281). Cuebot
// exposes SetMinCores / SetMaxCores as two RPCs, so we POST both in turn;
// one toast on full success, and if the min call fails we skip max and
// surface the error. Returns true on full success, false otherwise, so the
// dialog can gate its optimistic row update on success (mirrors performAction).
export async function setJobCores(job: Job, minCores: number, maxCores: number): Promise<boolean> {
  try {
    const minRes = await accessActionApi("/api/job/action/setmincores", [JSON.stringify({ job, val: minCores })]);
    if (!minRes?.success) throw new Error(minRes?.error ?? "Failed to set min cores");
    const maxRes = await accessActionApi("/api/job/action/setmaxcores", [JSON.stringify({ job, val: maxCores })]);
    if (!maxRes?.success) throw new Error(maxRes?.error ?? "Failed to set max cores");
    toastSuccess(`Set cores ${minCores}-${maxCores} on ${job.name}`);
    return true;
  } catch (error) {
    handleError(error, `Error setting cores on ${job.name}`);
    return false;
  }
}

export async function setJobMaxRetries(job: Job, maxRetries: number) {
  const endpoint = "/api/job/action/setmaxretries";
  await performAction(endpoint, [JSON.stringify({ job, max_retries: maxRetries })], `Set max retries ${maxRetries} on ${job.name}`);
}

export async function setJobAutoEat(job: Job, value: boolean) {
  const endpoint = "/api/job/action/setautoeat";
  await performAction(endpoint, [JSON.stringify({ job, value })], `Auto-Eat ${value ? "ON" : "OFF"} on ${job.name}`);
}

export async function dropJobDepends(job: Job, target: "INTERNAL" | "EXTERNAL") {
  const endpoint = "/api/job/action/dropdepends";
  await performAction(endpoint, [JSON.stringify({ job, target })], `Dropped ${target.toLowerCase()} depends on ${job.name}`);
  // Drop dependencies materially changes the Jobs table (a job stuck in
  // DEPENDENCY state can flip to IN PROGRESS / PAUSED the moment its
  // depends are removed) and invalidates the Group-By Dependent tree
  // cache. Dispatch two events so the table doesn't have to wait for
  // the 5s autoload tick to catch up:
  //   - cueweb:refresh-now triggers an immediate addUsersJobs() poll.
  //   - cueweb:depends-changed clears the dependency-graph cache and
  //     bumps the tree-fetch token so chevrons re-resolve.
  if (typeof window !== "undefined") {
    window.dispatchEvent(new CustomEvent("cueweb:refresh-now"));
    window.dispatchEvent(new CustomEvent("cueweb:depends-changed"));
  }
}

// Fetch the depend.DependSeq for a job (mirrors Job.getDepends() in pycue).
// Returns the raw list of Depend protos so the View Dependencies dialog can
// render Type / Target / Active / OnJob / OnLayer / OnFrame. Errors are
// surfaced via accessGetApi's handleError; on failure we return [].
export async function fetchJobDepends(job: Job): Promise<any[]> {
  const endpoint = "/api/job/action/getdepends";
  const body = JSON.stringify({ job });
  const data = await accessGetApi(endpoint, body);
  if (!data) return [];
  // The REST gateway wraps the DependSeq under `depends.depends`. Tolerate
  // both shapes so the dialog stays robust to minor proto-gateway shifts.
  const seq = data?.depends?.depends ?? data?.depends ?? [];
  return Array.isArray(seq) ? seq : [];
}

// Wizard dispatchers. Each takes a *cross-product* of sources x targets:
// the wizard's pickers are all multi-select (CueGUI parity), so one
// Done click can fan out to len(sources) * len(targets) parallel RPCs.
// The Cuebot REST gateway is name- or id-keyed on each target object,
// so we pass both for resolution flexibility.

type ObjRef = { id: string; name: string };

function fanOutLabel(count: number, kind: string): string {
  if (count === 1) return `1 ${kind}`;
  return `${count} ${kind}s`;
}

// Build a cross-product body array. Skips empty source / target lists
// (treating them as "no work") and returns [] when either is empty.
function crossBodies<S, T>(sources: S[], targets: T[], make: (s: S, t: T) => unknown): string[] {
  if (sources.length === 0 || targets.length === 0) return [];
  const out: string[] = [];
  for (const s of sources) for (const t of targets) out.push(JSON.stringify(make(s, t)));
  return out;
}

// Job-On-X: source is always THIS job (singleton). Target list fans out.
export async function createDependOnJob(thisJob: Job, onJobs: ObjRef[]) {
  if (onJobs.length === 0) return;
  const endpoint = "/api/job/action/createdependonjob";
  const bodyAr = onJobs.map((j) => JSON.stringify({ job: thisJob, on_job: { id: j.id, name: j.name } }));
  await performAction(endpoint, bodyAr, `Added Job-On-Job depend: ${thisJob.name} -> ${fanOutLabel(bodyAr.length, "job")}`);
}

export async function createDependOnLayer(thisJob: Job, onLayers: ObjRef[]) {
  if (onLayers.length === 0) return;
  const endpoint = "/api/job/action/createdependonlayer";
  const bodyAr = onLayers.map((l) => JSON.stringify({ job: thisJob, layer: { id: l.id, name: l.name } }));
  await performAction(endpoint, bodyAr, `Added Job-On-Layer depend: ${thisJob.name} -> ${fanOutLabel(bodyAr.length, "layer")}`);
}

export async function createDependOnFrame(thisJob: Job, onFrames: ObjRef[]) {
  if (onFrames.length === 0) return;
  const endpoint = "/api/job/action/createdependonframe";
  const bodyAr = onFrames.map((f) => JSON.stringify({ job: thisJob, frame: { id: f.id, name: f.name } }));
  await performAction(endpoint, bodyAr, `Added Job-On-Frame depend: ${thisJob.name} -> ${fanOutLabel(bodyAr.length, "frame")}`);
}

// Layer-On-X: M source layers in THIS job x N targets = M*N RPCs.
export async function createLayerOnJob(thisJob: Job, sourceLayers: ObjRef[], onJobs: ObjRef[]) {
  const bodyAr = crossBodies(sourceLayers, onJobs, (l, j) => ({
    layer: { id: l.id, name: l.name },
    job: { id: j.id, name: j.name },
  }));
  if (bodyAr.length === 0) return;
  await performAction("/api/layer/action/createdependonjob", bodyAr,
    `Added Layer-On-Job depend: ${thisJob.name} (${fanOutLabel(bodyAr.length, "pair")})`);
}

export async function createLayerOnLayer(thisJob: Job, sourceLayers: ObjRef[], onLayers: ObjRef[]) {
  const bodyAr = crossBodies(sourceLayers, onLayers, (s, t) => ({
    layer: { id: s.id, name: s.name },
    depend_on_layer: { id: t.id, name: t.name },
  }));
  if (bodyAr.length === 0) return;
  await performAction("/api/layer/action/createdependonlayer", bodyAr,
    `Added Layer-On-Layer depend: ${thisJob.name} (${fanOutLabel(bodyAr.length, "pair")})`);
}

export async function createLayerOnFrame(thisJob: Job, sourceLayers: ObjRef[], onFrames: ObjRef[]) {
  const bodyAr = crossBodies(sourceLayers, onFrames, (l, f) => ({
    layer: { id: l.id, name: l.name },
    frame: { id: f.id, name: f.name },
  }));
  if (bodyAr.length === 0) return;
  await performAction("/api/layer/action/createdependonframe", bodyAr,
    `Added Layer-On-Frame depend: ${thisJob.name} (${fanOutLabel(bodyAr.length, "pair")})`);
}

// Frame-By-Frame: M source layers x N target layers = M*N FBF pairs.
export async function createFrameByFrameDepend(
  thisJob: Job,
  sourceLayers: ObjRef[],
  dependLayers: ObjRef[],
  anyFrame: boolean = false,
) {
  const bodyAr = crossBodies(sourceLayers, dependLayers, (s, t) => ({
    layer: { id: s.id, name: s.name },
    depend_layer: { id: t.id, name: t.name },
    any_frame: anyFrame,
  }));
  if (bodyAr.length === 0) return;
  await performAction("/api/layer/action/createframebyframedepend", bodyAr,
    `Added Frame-By-Frame depend: ${thisJob.name} (${fanOutLabel(bodyAr.length, "pair")})`);
}

// Hard Depend (JFBF, "Frame By Frame for all layers"): client-side. For
// each picked target job, pair THIS job's layers with the target job's
// layers by `layer.type` and fire CreateFrameByFrameDependency for every
// match. With multiple target jobs we accumulate every pair across them
// into a single performAction call so the user gets one summary toast.
export async function createHardDepend(
  thisJob: Job,
  thisJobLayers: { id: string; name: string; type?: string }[],
  perTargetJobLayers: { job: ObjRef; layers: { id: string; name: string; type?: string }[] }[],
) {
  const bodyAr: string[] = [];
  let matchedJobs = 0;
  for (const { layers: targetLayers } of perTargetJobLayers) {
    let matched = 0;
    for (const src of thisJobLayers) {
      const match = targetLayers.find((t) => t.type && src.type && t.type === src.type);
      if (!match) continue;
      matched += 1;
      bodyAr.push(JSON.stringify({
        layer: { id: src.id, name: src.name },
        depend_layer: { id: match.id, name: match.name },
        any_frame: false,
      }));
    }
    if (matched > 0) matchedJobs += 1;
  }
  if (bodyAr.length === 0) {
    toastWarning(`No matching layer types found for Hard Depend on ${thisJob.name}.`);
    return;
  }
  await performAction("/api/layer/action/createframebyframedepend", bodyAr,
    `Added Hard Depend: ${thisJob.name} -> ${fanOutLabel(matchedJobs, "job")} (${fanOutLabel(bodyAr.length, "layer pair")})`);
}

// Frame-On-X: M source frames x N targets = M*N RPCs.
export async function createFrameOnJob(thisJob: Job, sourceFrames: ObjRef[], onJobs: ObjRef[]) {
  const bodyAr = crossBodies(sourceFrames, onJobs, (f, j) => ({
    frame: { id: f.id, name: f.name },
    job: { id: j.id, name: j.name },
  }));
  if (bodyAr.length === 0) return;
  await performAction("/api/frame/action/createdependonjob", bodyAr,
    `Added Frame-On-Job depend: ${thisJob.name} (${fanOutLabel(bodyAr.length, "pair")})`);
}

export async function createFrameOnLayer(thisJob: Job, sourceFrames: ObjRef[], onLayers: ObjRef[]) {
  const bodyAr = crossBodies(sourceFrames, onLayers, (f, l) => ({
    frame: { id: f.id, name: f.name },
    layer: { id: l.id, name: l.name },
  }));
  if (bodyAr.length === 0) return;
  await performAction("/api/frame/action/createdependonlayer", bodyAr,
    `Added Frame-On-Layer depend: ${thisJob.name} (${fanOutLabel(bodyAr.length, "pair")})`);
}

export async function createFrameOnFrame(thisJob: Job, sourceFrames: ObjRef[], onFrames: ObjRef[]) {
  const bodyAr = crossBodies(sourceFrames, onFrames, (s, t) => ({
    frame: { id: s.id, name: s.name },
    depend_on_frame: { id: t.id, name: t.name },
  }));
  if (bodyAr.length === 0) return;
  await performAction("/api/frame/action/createdependonframe", bodyAr,
    `Added Frame-On-Frame depend: ${thisJob.name} (${fanOutLabel(bodyAr.length, "pair")})`);
}

// Layer-On-Simulation-Frame: pycue / CueGUI implement this by looping
// FrameInterface.CreateDependencyOnFrame for every frame in each source
// layer, all pointing at the chosen sim frame(s). We accept the already-
// expanded source-frame list per source layer (the wizard fetches and
// filters those) plus the target frames, then cross-product.
export async function createLayerOnSimFrame(
  thisJob: Job,
  sourceLayerNames: string[],
  sourceFrames: ObjRef[],
  onFrames: ObjRef[],
) {
  if (sourceFrames.length === 0) {
    toastWarning(`No frames found in source layer${sourceLayerNames.length > 1 ? "s" : ""} ${sourceLayerNames.join(", ")}.`);
    return;
  }
  const bodyAr = crossBodies(sourceFrames, onFrames, (s, t) => ({
    frame: { id: s.id, name: s.name },
    depend_on_frame: { id: t.id, name: t.name },
  }));
  if (bodyAr.length === 0) return;
  await performAction("/api/frame/action/createdependonframe", bodyAr,
    `Added Layer-On-Sim-Frame depend: ${thisJob.name} (${fanOutLabel(bodyAr.length, "frame pair")})`);
}

/**************************************/
/* Table header menu functions        */
/**************************************/

export function getItemFromLocalStorage(itemKey: string, initialItemValue: string) {
  const itemFromStorage = JSON.parse(localStorage.getItem(itemKey) || initialItemValue);
  return itemFromStorage;
};

export function setItemInLocalStorage(itemKey: string, item: string) {
  localStorage.setItem(itemKey, item);
};

export function getJobsFromSelectedRows(table: any): Job[] {
  const selectedRows: Row<Job>[] = table.getSelectedRowModel().rows;
  return selectedRows.map(row => row.original);
}

export function eatJobsDeadFramesFromSelectedRows(table: any) {
  const jobs = getJobsFromSelectedRows(table).filter(job => job.state !== "FINISHED");
  if (jobs.length === 0) {
    toastWarning("Please select unfinished jobs");
  } else {
    eatJobsDeadFrames(jobs);
  }
}

export function retryJobsDeadFramesFromSelectedRows(table: any) {
  const jobs = getJobsFromSelectedRows(table).filter(job => job.state !== "FINISHED");
  if (jobs.length === 0) {
    toastWarning("Please select unfinished jobs");
  } else {
    retryJobsDeadFrames(jobs);
  }
}

export function pauseJobsFromSelectedRows(table: any) {
  const jobs = getJobsFromSelectedRows(table).filter(job => job.state !== "FINISHED");
  if (jobs.length === 0) {
    toastWarning("Please select unfinished jobs");
  } else {
    pauseJobs(jobs);
  }
}

export function unpauseJobsFromSelectedRows(table: any) {
  const jobs = getJobsFromSelectedRows(table).filter(job => job.state !== "FINISHED");
  if (jobs.length === 0) {
    toastWarning("Please select unfinished jobs");
  } else {
    unpauseJobs(jobs);
  }
}

export function killJobFromSelectedRows(table: any, username: string) {
  const reason = `Manual job kill request in Cueweb's menu bar by ${username}`;
  const jobs = getJobsFromSelectedRows(table).filter(job => job.state !== "FINISHED");
  if (jobs.length === 0) {
    toastWarning("Please select unfinished jobs");
  } else {
    killJobs(jobs, username, reason);
  }
}

/***************************************************/
/* Context menu functions for Jobs, Layers, Frames */
/***************************************************/
export function unmonitorJobGivenRow(
  row: Row<any>, tableData: Job[], tableDataUnfiltered: Job[],
  rowSelection: { [key: number]: boolean },
  setTableData: React.Dispatch<React.SetStateAction<Job[]>>,
  setTableDataUnfiltered: React.Dispatch<React.SetStateAction<Job[]>>,
  setRowSelection: React.Dispatch<React.SetStateAction<{ [key: number]: boolean }>>,
  tableStorageName: string, unfilteredTableStorageName: string
) {
  const jobToUnmonitor = row.original;
  const updatedTableData = tableData.filter(job => job.id !== jobToUnmonitor.id);
  const updatedTableDataUnfiltered = tableDataUnfiltered.filter(job => job.id !== jobToUnmonitor.id);
  
  const updatedRowSelection = { ...rowSelection };
  if (row.original.id in updatedRowSelection) {
    delete updatedRowSelection[row.original.id];
  }

  setTableData(updatedTableData);
  setTableDataUnfiltered(updatedTableDataUnfiltered);
  setItemInLocalStorage(tableStorageName, JSON.stringify(updatedTableData));
  setItemInLocalStorage(unfilteredTableStorageName, JSON.stringify(updatedTableDataUnfiltered));
  setRowSelection(updatedRowSelection);
}

export function pauseJobGivenRow(row: Row<any>) {
    const jobs = [row.original];
    pauseJobs(jobs);
}

export function retryJobsDeadFramesGivenRow(row: Row<any>) {
    const jobs = [row.original];
    retryJobsDeadFrames(jobs);
}

export function eatJobsDeadFramesGivenRow(row: Row<any>) {
    const jobs = [row.original];
    eatJobsDeadFrames(jobs);
}

export function killJobGivenRow(row: Row<any>, username: string) {
    const jobs = [row.original]
    const reason = `Manual job kill request in Cueweb's context menu by ${username}`;
    killJobs(jobs, username, reason);
}

/********************************/
/* Layer context menu functions */
/********************************/

export function killLayerGivenRow(row: Row<any>, username: string) {
    const layers = [row.original]
    const reason = `Manual layer kill request in Cueweb's context menu by ${username}`;
    killLayers(layers, username, reason);
}

export function eatLayerFramesGivenRow(row: Row<any>) {
    const layers = [row.original]
    eatLayersFrames(layers);
}

export function retryLayerFramesGivenRow(row: Row<any>) {
    const layers = [row.original]
    retryLayersFrames(layers);
}

export function retryLayerDeadFramesGivenRow(row: Row<any>) {
    const layers = [row.original]
    retryLayersDeadFrames(layers);
}

/********************************/
/* Frame context menu functions */
/********************************/

export function retryFrameGivenRow(row: Row<any>) {
    const frames = [row.original];
    retryFrames(frames);
}

export function killFrameGivenRow(row: Row<any>, username: string) {
    const frames = [row.original];
    const reason = `Manual frame kill request in Cueweb's context menu by ${username}`;
    killFrames(frames, username, reason);
}

export function eatFrameGivenRow(row: Row<any>) {
    const frames = [row.original];
    eatFrames(frames);
}

/********************************/
/* Host context menu functions  */
/********************************/

// Right-click "Lock"/"Unlock" handlers. Rather than calling the action
// directly, these dispatch a CustomEvent that the HostLockDialog (mounted
// on the hosts page) listens for, so the user gets a confirmation step
// before the host leaves / rejoins the booking pool. Decoupled the same
// way as setPriorityGivenRow so the free-function context-menu handlers
// don't need to reach into the table's component state.
export function lockHostGivenRow(row: Row<any>) {
  if (typeof window === "undefined") return;
  window.dispatchEvent(
    new CustomEvent("cueweb:open-host-lock", {
      detail: { hosts: [row.original as Host], action: "lock" },
    }),
  );
}

export function unlockHostGivenRow(row: Row<any>) {
  if (typeof window === "undefined") return;
  window.dispatchEvent(
    new CustomEvent("cueweb:open-host-lock", {
      detail: { hosts: [row.original as Host], action: "unlock" },
    }),
  );
}

// Immediate reboot kills running frames, so route it through the
// confirmation dialog (cueweb:open-host-reboot -> HostRebootDialog)
// rather than firing straight away.
export function rebootHostGivenRow(row: Row<any>) {
  if (typeof window === "undefined") return;
  window.dispatchEvent(
    new CustomEvent("cueweb:open-host-reboot", {
      detail: { hosts: [row.original as Host] },
    }),
  );
}

// Reboot-when-idle is non-destructive (it waits for running frames to
// finish before rebooting), so it fires immediately without a confirm
// step, mirroring CueGUI. Optimistically flip the row to REBOOT_WHEN_IDLE
// once the request is sent so the table updates without waiting for the
// next poll.
export function rebootHostWhenIdleGivenRow(row: Row<any>) {
  const host = row.original as Host;
  void rebootHostsWhenIdle([host]).then((ok) => {
    // Only patch the row optimistically when the action actually succeeded;
    // performAction swallows errors (returning false) and toasts them, so a
    // failed request leaves the row at its true state instead of flickering.
    if (!ok || typeof window === "undefined") return;
    window.dispatchEvent(
      new CustomEvent("cueweb:hosts-changed", {
        detail: { hostIds: [host.id], patch: { state: "REBOOT_WHEN_IDLE" } },
      }),
    );
  });
}

// "Edit Tags..." opens the tag editor dialog (cueweb:open-host-tags ->
// EditHostTagsDialog), which loads existing tags for autocomplete and
// diffs the working set into add/remove calls on save.
export function editHostTagsGivenRow(row: Row<any>) {
  if (typeof window === "undefined") return;
  window.dispatchEvent(
    new CustomEvent("cueweb:open-host-tags", {
      detail: { hosts: [row.original as Host] },
    }),
  );
}

/**********************************************/
/* Per-row wrappers for the expanded job menu */
/**********************************************/

export function unpauseJobGivenRow(row: Row<any>) {
  unpauseJobs([row.original]);
}

export function autoEatOnGivenRow(row: Row<any>) {
  setJobAutoEat(row.original, true);
}

export function autoEatOffGivenRow(row: Row<any>) {
  setJobAutoEat(row.original, false);
}

export function dropExternalDependsGivenRow(row: Row<any>) {
  dropJobDepends(row.original, "EXTERNAL");
}

export function dropInternalDependsGivenRow(row: Row<any>) {
  dropJobDepends(row.original, "INTERNAL");
}

// Right-click "View Dependencies..." handler. Dispatches a CustomEvent
// that the ViewDependenciesDialog (mounted at the page level) listens for;
// the dialog opens, fetches the job's DependSeq via fetchJobDepends, and
// renders the CueGUI-parity Type / Target / Active / OnJob / OnLayer /
// OnFrame table.
export function viewDependenciesGivenRow(row: Row<any>) {
  const job = row.original as Job;
  if (typeof window === "undefined") return;
  window.dispatchEvent(
    new CustomEvent("cueweb:open-view-dependencies", { detail: { job } }),
  );
}

// Right-click "Dependency Wizard..." handler. Dispatches a CustomEvent
// that the DependencyWizardDialog (mounted at the page level) listens
// for; the wizard walks the user through picking a dependency type and
// target object, then dispatches to the right CreateDependencyOn* RPC.
export function dependencyWizardGivenRow(row: Row<any>) {
  const job = row.original as Job;
  if (typeof window === "undefined") return;
  window.dispatchEvent(
    new CustomEvent("cueweb:open-dependency-wizard", { detail: { job } }),
  );
}

// Right-click "Set Priority..." handler. Dispatches a CustomEvent
// that the SetPriorityDialog (mounted at the page level) listens for;
// the dialog opens with a slider + number input pre-filled with the
// row's current priority and calls setJobPriority on Apply. Decoupled
// this way so the free-function context-menu handlers don't need to
// reach into the table's component state.
export function setPriorityGivenRow(row: Row<any>) {
  const job = row.original as Job;
  if (typeof window === "undefined") return;
  window.dispatchEvent(
    new CustomEvent("cueweb:open-set-priority", {
      detail: { job },
    }),
  );
}

// Right-click "Set Min/Max Cores..." handler. Dispatches a CustomEvent that
// the SetCoresDialog (mounted at the page level) listens for; the dialog
// opens with Min/Max number inputs pre-filled with the row's current cores
// and a client-side min<=max guard, and calls setJobCores on Apply.
// Decoupled this way so the free-function context-menu handlers don't need
// to reach into the table's component state.
export function setCoresGivenRow(row: Row<any>) {
  const job = row.original as Job;
  if (typeof window === "undefined") return;
  window.dispatchEvent(
    new CustomEvent("cueweb:open-set-cores", {
      detail: { job },
    }),
  );
}

// Right-click "Email Artist..." handler. Dispatches a CustomEvent that
// the EmailArtistDialog (mounted at the page level) listens for; the
// dialog opens pre-filled with From/To/CC/Subject/Body derived from the
// job and the deployment's email domain. Decoupled this way so the
// free-function context-menu handlers don't need to reach into the
// table's component state.
export function emailArtistGivenRow(row: Row<any>) {
  const job = row.original as Job;
  if (typeof window === "undefined") return;
  window.dispatchEvent(
    new CustomEvent("cueweb:open-email-artist", {
      detail: { job },
    }),
  );
}

// Right-click "Request Cores..." handler. Dispatches a CustomEvent
// that the RequestCoresDialog (mounted at the page level) listens for;
// the dialog opens with an email composer pre-filled with To/CC/Subject
// and an auto-populated body listing the layers with frames remaining
// (waiting + running). User adds the wanted completion date and any
// notes, hits Send, and the OS hands the mail off to their default
// client via a mailto: URL. Decoupled this way so the free-function
// context-menu handlers don't need to reach into the table's component
// state.
export function requestCoresGivenRow(row: Row<any>) {
  const job = row.original as Job;
  if (typeof window === "undefined") return;
  window.dispatchEvent(
    new CustomEvent("cueweb:open-request-cores", {
      detail: { job },
    }),
  );
}

// Right-click "Subscribe to Job" handler. Dispatches a CustomEvent that
// the SubscribeToJobDialog listens for. The dialog mirrors CueGUI's
// SubscribeToJobDialog: a small form with the job name, a (read-only)
// From address and an editable To address. Save calls
// addJobSubscriber() which forwards to the AddSubscriber RPC on Cuebot;
// when the job finishes Cuebot sends an email to the subscriber.
export function subscribeToJobGivenRow(row: Row<any>) {
  const job = row.original as Job;
  if (typeof window === "undefined") return;
  window.dispatchEvent(
    new CustomEvent("cueweb:open-subscribe-to-job", {
      detail: { job },
    }),
  );
}

// Right-click "Unbook..." handler. Dispatches a CustomEvent that the
// UnbookDialog (mounted at the page level) listens for; the dialog opens
// with an optional "Kill unbooked frames?" checkbox and calls unbookJob on
// confirm. Decoupled this way so the free-function context-menu handlers
// don't need to reach into the table's component state.
export function unbookGivenRow(row: Row<any>) {
  const job = row.original as Job;
  if (typeof window === "undefined") return;
  window.dispatchEvent(
    new CustomEvent("cueweb:open-unbook", {
      detail: { job },
    }),
  );
}

// Calls the Cuebot AddSubscriber RPC to register an email subscriber for
// the job. Cuebot sends notification email to subscriber on job completion.
export async function addJobSubscriber(job: Job, subscriber: string) {
  const endpoint = "/api/job/action/addsubscriber";
  const body = JSON.stringify({ job, subscriber });
  await performAction(endpoint, [body], `Subscribed ${subscriber} to ${job.name}`);
}

export function setMaxRetriesGivenRow(row: Row<any>) {
  const job = row.original as Job;
  const raw = window.prompt(`Set max retries for ${job.name}`, "3");
  if (raw === null) return;
  // Strict non-negative integer match; same parseInt caveats as above.
  const trimmed = raw.trim();
  if (!/^\d+$/.test(trimmed)) {
    toastWarning("Max retries must be a non-negative integer");
    return;
  }
  setJobMaxRetries(job, Number.parseInt(trimmed, 10));
}

// Pure-client clipboard helpers; surface a toast on success/failure so the
// user gets the same feedback as for back-end actions.

/** Copy `text` to the clipboard, falling back to the legacy execCommand
 * path when the modern Clipboard API is unavailable.
 *
 * `navigator.clipboard.writeText()` is only exposed in **secure contexts**
 * (HTTPS, `http://localhost`, or `file://`). When CueWeb is served from a
 * LAN IP over plain HTTP - e.g. a Smartphone reaching the Computer/Server at
 * `http://XXX.XXX.X.XXX:3000` - the API either isn't there or rejects
 * with a SecurityError. The execCommand fallback still works on Smartphone
 * browser (e.g.  iOS Safari and Android Chrome).
 */
async function copyTextToClipboard(text: string): Promise<void> {
  // Modern path - requires a secure context. Wrap in try/catch so that
  // a rejection (revoked permission, transient browser quirk, sandboxed
  // iframe denying clipboard-write, etc.) doesn't short-circuit the
  // legacy execCommand fallback below.
  if (
    typeof navigator !== "undefined"
    && navigator.clipboard
    && typeof window !== "undefined"
    && window.isSecureContext
  ) {
    try {
      await navigator.clipboard.writeText(text);
      return;
    } catch {
      // Fall through to the legacy textarea + execCommand path.
    }
  }
  // Legacy fallback for insecure contexts (HTTP LAN IPs, etc.).
  if (typeof document === "undefined") {
    throw new Error("Clipboard unavailable: no document");
  }
  const textarea = document.createElement("textarea");
  textarea.value = text;
  // readonly + tiny, transparent overlay keeps Smartphone from popping the soft
  // keyboard and from visually flashing the textarea during the copy.
  textarea.setAttribute("readonly", "");
  textarea.style.position = "fixed";
  textarea.style.top = "0";
  textarea.style.left = "0";
  textarea.style.width = "1px";
  textarea.style.height = "1px";
  textarea.style.padding = "0";
  textarea.style.border = "0";
  textarea.style.outline = "0";
  textarea.style.boxShadow = "none";
  textarea.style.background = "transparent";
  textarea.style.opacity = "0";
  document.body.appendChild(textarea);
  try {
    // iOS Safari requires an explicit selection range; plain .select()
    // doesn't actually select on mobile WebKit.
    if (/iPad|iPhone|iPod/.test(navigator.userAgent)) {
      const range = document.createRange();
      range.selectNodeContents(textarea);
      const sel = window.getSelection();
      sel?.removeAllRanges();
      sel?.addRange(range);
      textarea.setSelectionRange(0, text.length);
    } else {
      textarea.focus();
      textarea.select();
    }
    const ok = document.execCommand("copy");
    if (!ok) throw new Error("execCommand('copy') returned false");
  } finally {
    document.body.removeChild(textarea);
  }
}

export async function copyJobNameGivenRow(row: Row<any>) {
  const job = row.original as Job;
  try {
    await copyTextToClipboard(job.name);
    toastSuccess(`Copied job name: ${job.name}`);
  } catch (err) {
    handleError(err, "Could not copy job name to clipboard");
  }
}

export async function copyLogDirGivenRow(row: Row<any>) {
  const job = row.original as Job;
  if (!job.logDir) {
    toastWarning("Job has no logDir set");
    return;
  }
  try {
    await copyTextToClipboard(job.logDir);
    toastSuccess(`Copied log directory: ${job.logDir}`);
  } catch (err) {
    handleError(err, "Could not copy log directory to clipboard");
  }
}

export async function copyLayerNameGivenRow(row: Row<any>) {
  const layer = row.original as Layer;
  try {
    await copyTextToClipboard(layer.name);
    toastSuccess(`Copied layer name: ${layer.name}`);
  } catch (err) {
    handleError(err, "Could not copy layer name to clipboard");
  }
}

export async function copyFrameNameGivenRow(row: Row<any>) {
  const frame = row.original as Frame;
  try {
    await copyTextToClipboard(frame.name);
    toastSuccess(`Copied frame name: ${frame.name}`);
  } catch (err) {
    handleError(err, "Could not copy frame name to clipboard");
  }
}

/** Copy the absolute rqlog path for a frame. Requires the parent job because
 * the log filename is `<job.name>.<frame.name>.rqlog` inside `job.logDir`. */
export async function copyFrameLogPath(job: Job | undefined, row: Row<any>) {
  if (!job) {
    toastWarning("Frame log path unavailable (no parent job context)");
    return;
  }
  const frame = row.original as Frame;
  if (!job.logDir) {
    toastWarning("Job has no logDir set");
    return;
  }
  const fullPath = getFrameLogDir(job, frame);
  try {
    await copyTextToClipboard(fullPath);
    toastSuccess(`Copied log path: ${fullPath}`);
  } catch (err) {
    handleError(err, "Could not copy log path to clipboard");
  }
}
/**************************************/
// Show actions (CueCommander Shows window parity)
/**************************************/

// Show mutations call accessActionApi directly (no per-call success toast) so
// the calling dialog can show a single "Saved" toast after applying several
// changes at once. Errors are still surfaced as toasts by accessActionApi.
async function showAction(endpoint: string, body: object): Promise<boolean> {
  const result = await accessActionApi(endpoint, [JSON.stringify(body)]);
  return !!result?.success;
}

export async function enableShowBooking(show: Show, enabled: boolean): Promise<boolean> {
  return showAction("/api/show/action/enablebooking", { show, enabled });
}

export async function enableShowDispatching(show: Show, enabled: boolean): Promise<boolean> {
  return showAction("/api/show/action/enabledispatching", { show, enabled });
}

export async function setShowDefaultMaxCores(show: Show, maxCores: number): Promise<boolean> {
  return showAction("/api/show/action/setdefaultmaxcores", { show, max_cores: maxCores });
}

export async function setShowDefaultMinCores(show: Show, minCores: number): Promise<boolean> {
  return showAction("/api/show/action/setdefaultmincores", { show, min_cores: minCores });
}

export async function setShowCommentEmail(show: Show, email: string): Promise<boolean> {
  return showAction("/api/show/action/setcommentemail", { show, email });
}

export async function createShowSubscription(
  show: Show,
  allocationId: string,
  size: number,
  burst: number,
): Promise<boolean> {
  return showAction("/api/show/action/createsubscription", {
    show,
    allocation_id: allocationId,
    size,
    burst,
  });
}

// Context-menu dispatchers: open the page-level dialogs via CustomEvent so the
// free-function handlers stay free of component state (same pattern as hosts).
export function showPropertiesGivenRow(row: Row<any>) {
  if (typeof window === "undefined") return;
  window.dispatchEvent(
    new CustomEvent("cueweb:open-show-properties", {
      detail: { show: row.original as Show },
    }),
  );
}

export function createSubscriptionGivenRow(row: Row<any>) {
  if (typeof window === "undefined") return;
  window.dispatchEvent(
    new CustomEvent("cueweb:open-create-subscription", {
      detail: { show: row.original as Show },
    }),
  );
}

// Subscription mutations (CueGUI SubscriptionActions parity). new_size / burst
// are passed in centcores (cores * 100); the dialogs convert, matching
// CueGUI's int(value * 100.0). No per-call success toast - the dialog shows a
// single toast after the call resolves.
export async function setSubscriptionSize(
  subscription: Subscription,
  newSizeCentcores: number,
): Promise<boolean> {
  const result = await accessActionApi(
    "/api/subscription/setsize",
    [JSON.stringify({ subscription, new_size: newSizeCentcores })],
  );
  return !!result?.success;
}

export async function setSubscriptionBurst(
  subscription: Subscription,
  burstCentcores: number,
): Promise<boolean> {
  const result = await accessActionApi(
    "/api/subscription/setburst",
    [JSON.stringify({ subscription, burst: burstCentcores })],
  );
  return !!result?.success;
}

export async function deleteSubscription(subscription: Subscription): Promise<boolean> {
  const result = await accessActionApi(
    "/api/subscription/delete",
    [JSON.stringify({ subscription })],
  );
  return !!result?.success;
}

/**************************************/
// Limit actions (CueCommander Limits window parity)
/**************************************/

// Limit mutations key on the limit name (the proto requests take name /
// old_name, not an id or object). They call accessActionApi directly so the
// calling dialog can show a single toast; errors are surfaced by accessActionApi.
async function limitAction(endpoint: string, body: object): Promise<boolean> {
  const result = await accessActionApi(endpoint, [JSON.stringify(body)]);
  return !!result?.success;
}

export async function createLimit(name: string, maxValue: number): Promise<boolean> {
  return limitAction("/api/limit/action/create", { name, max_value: maxValue });
}

export async function deleteLimit(name: string): Promise<boolean> {
  return limitAction("/api/limit/action/delete", { name });
}

export async function renameLimit(oldName: string, newName: string): Promise<boolean> {
  return limitAction("/api/limit/action/rename", { old_name: oldName, new_name: newName });
}

export async function setLimitMaxValue(name: string, maxValue: number): Promise<boolean> {
  return limitAction("/api/limit/action/setmaxvalue", { name, max_value: maxValue });
}

// Context-menu dispatchers: open the page-level subscription dialogs via
// CustomEvent so the free-function handlers stay free of component state
// (same pattern as the Shows window).
export function editSubscriptionSizeGivenRow(row: Row<any>) {
  if (typeof window === "undefined") return;
  window.dispatchEvent(
    new CustomEvent(OPEN_EDIT_SUBSCRIPTION_SIZE_EVENT, {
      detail: { subscription: row.original as Subscription },
    }),
  );
}

// Context-menu dispatchers: open the page-level dialogs via CustomEvent so the
// free-function handlers stay free of component state (same pattern as hosts/shows).
export function editLimitMaxValueGivenRow(row: Row<any>) {
  if (typeof window === "undefined") return;
  window.dispatchEvent(
    new CustomEvent("cueweb:open-limit-edit-max-value", {
      detail: { limit: row.original as Limit },
    }),
  );
}

export function editSubscriptionBurstGivenRow(row: Row<any>) {
  if (typeof window === "undefined") return;
  window.dispatchEvent(
    new CustomEvent(OPEN_EDIT_SUBSCRIPTION_BURST_EVENT, {
      detail: { subscription: row.original as Subscription },
    }),
  );
}

export function renameLimitGivenRow(row: Row<any>) {
  if (typeof window === "undefined") return;
  window.dispatchEvent(
    new CustomEvent("cueweb:open-limit-rename", {
      detail: { limit: row.original as Limit },
    }),
  );
}

export function deleteSubscriptionGivenRow(row: Row<any>) {
  if (typeof window === "undefined") return;
  window.dispatchEvent(
    new CustomEvent(OPEN_DELETE_SUBSCRIPTION_EVENT, {
      detail: { subscription: row.original as Subscription },
    }),
  );
}

export function deleteLimitGivenRow(row: Row<any>) {
  if (typeof window === "undefined") return;
  window.dispatchEvent(
    new CustomEvent("cueweb:open-limit-delete", {
      detail: { limit: row.original as Limit },
    }),
  );
}
