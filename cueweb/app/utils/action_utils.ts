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
import { getFrameLogDir, getJobForLayer, JobComment } from "./get_utils";
import { handleError, toastSuccess, toastWarning } from "./notify_utils";

/**************************************/
// Helper function for API calls
/**************************************/

export async function performAction(endpoint: string, bodyAr: string[], successMessage: string) {
  if (bodyAr.length === 0) return;

  try {
    const result = await accessActionApi(endpoint, bodyAr);
    if (result?.success) {
      toastSuccess(successMessage);
    } else {
      throw new Error(result.error);
    }
  } catch (error) {
    handleError(error, `Error performing action for: ${endpoint}`);
  }
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
// Priority / retries / auto-eat / depends (CueGUI parity)
/**************************************/

export async function setJobPriority(job: Job, priority: number) {
  const endpoint = "/api/job/action/setpriority";
  await performAction(endpoint, [JSON.stringify({ job, val: priority })], `Set priority ${priority} on ${job.name}`);
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